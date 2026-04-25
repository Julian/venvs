use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::Path;

use anyhow::{Context, Result, bail};
use serde::{Deserialize, Serialize};

/// Raw TOML config as deserialized from virtualenvs.toml.
#[derive(Debug, Default, Deserialize)]
#[serde(default)]
struct RawConfig {
    bundle: BTreeMap<String, Vec<String>>,
    virtualenv: BTreeMap<String, RawVirtualEnvConfig>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(default)]
struct RawVirtualEnvConfig {
    python: Option<String>,
    install: Vec<String>,
    requirements: Vec<String>,
    #[serde(rename = "install-bundle")]
    install_bundle: Vec<String>,
    link: Vec<String>,
    #[serde(rename = "link-module")]
    link_module: Vec<String>,
    #[serde(rename = "post-commands")]
    post_commands: Vec<Vec<String>>,
}

/// A parsed link spec: source binary name -> target name in link dir.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LinkSpec {
    pub source: String,
    pub target: String,
}

/// A fully resolved virtualenv configuration.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ResolvedVirtualEnv {
    pub name: String,
    pub python: String,
    pub install: Vec<String>,
    pub requirements: Vec<String>,
    pub link: Vec<LinkSpec>,
    pub link_module: Vec<LinkSpec>,
    pub post_commands: Vec<Vec<String>>,
}

/// The fully resolved configuration.
#[derive(Debug)]
pub struct Config {
    pub virtualenvs: BTreeMap<String, ResolvedVirtualEnv>,
}

impl Config {
    pub fn from_file(path: &Path) -> Result<Self> {
        let contents = fs::read_to_string(path)
            .with_context(|| format!("reading config from {}", path.display()))?;
        Self::parse(&contents)
    }

    pub fn parse(s: &str) -> Result<Self> {
        let raw: RawConfig = toml::from_str(s).context("parsing virtualenvs.toml")?;
        Self::resolve(&raw)
    }

    fn resolve(raw: &RawConfig) -> Result<Self> {
        let mut virtualenvs = BTreeMap::new();

        for (name, raw_venv) in &raw.virtualenv {
            let resolved = resolve_venv(name, raw_venv, &raw.bundle)?;
            virtualenvs.insert(name.clone(), resolved);
        }

        check_for_duplicated_links(&virtualenvs)?;

        Ok(Config { virtualenvs })
    }
}

fn resolve_venv(
    name: &str,
    raw: &RawVirtualEnvConfig,
    bundles: &BTreeMap<String, Vec<String>>,
) -> Result<ResolvedVirtualEnv> {
    let mut install: Vec<String> = raw
        .install
        .iter()
        .map(|s| expand(s))
        .collect::<Result<_>>()?;

    for bundle_name in &raw.install_bundle {
        let bundle = bundles.get(bundle_name).with_context(|| {
            format!("virtualenv {name:?} references unknown bundle {bundle_name:?}")
        })?;
        for package in bundle {
            let expanded = expand(package)?;
            if !install.contains(&expanded) {
                install.push(expanded);
            }
        }
    }

    let requirements: Vec<String> = raw
        .requirements
        .iter()
        .map(|s| expand(s))
        .collect::<Result<_>>()?;

    Ok(ResolvedVirtualEnv {
        name: name.to_string(),
        python: raw.python.clone().unwrap_or_else(|| "python3".to_string()),
        install,
        requirements,
        link: parse_link_specs(&raw.link),
        link_module: parse_link_specs(&raw.link_module),
        post_commands: raw.post_commands.clone(),
    })
}

fn expand(s: &str) -> Result<String> {
    shellexpand::full(s)
        .map(std::borrow::Cow::into_owned)
        .map_err(|e| anyhow::anyhow!(e))
}

fn parse_link_specs(specs: &[String]) -> Vec<LinkSpec> {
    specs
        .iter()
        .map(|spec| match spec.split_once(':') {
            Some((source, target)) => LinkSpec {
                source: source.to_string(),
                target: target.to_string(),
            },
            None => LinkSpec {
                source: spec.clone(),
                target: spec.clone(),
            },
        })
        .collect()
}

fn check_for_duplicated_links(virtualenvs: &BTreeMap<String, ResolvedVirtualEnv>) -> Result<()> {
    let mut seen = BTreeSet::new();
    let mut duplicated = BTreeSet::new();

    for venv in virtualenvs.values() {
        for link in venv.link.iter().chain(venv.link_module.iter()) {
            if !seen.insert(&link.target) {
                duplicated.insert(link.target.clone());
            }
        }
    }

    if !duplicated.is_empty() {
        let names: Vec<_> = duplicated.into_iter().collect();
        bail!("duplicated link targets: {}", names.join(", "));
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_config() {
        let config = Config::parse("").unwrap();
        assert!(config.virtualenvs.is_empty());
    }

    #[test]
    fn basic_virtualenv() {
        let config = Config::parse(
            r#"
            [virtualenv.myenv]
            install = ["requests", "flask"]
            "#,
        )
        .unwrap();

        let venv = &config.virtualenvs["myenv"];
        assert_eq!(venv.name, "myenv");
        assert_eq!(venv.install, vec!["requests", "flask"]);
        assert_eq!(venv.python, "python3");
    }

    #[test]
    fn empty_virtualenv() {
        let config = Config::parse(
            r#"
            [virtualenv.myenv]
            "#,
        )
        .unwrap();

        let venv = &config.virtualenvs["myenv"];
        assert!(venv.install.is_empty());
        assert!(venv.requirements.is_empty());
        assert!(venv.link.is_empty());
        assert!(venv.link_module.is_empty());
        assert!(venv.post_commands.is_empty());
    }

    #[test]
    fn custom_python() {
        let config = Config::parse(
            r#"
            [virtualenv.myenv]
            python = "python3.11"
            "#,
        )
        .unwrap();

        assert_eq!(config.virtualenvs["myenv"].python, "python3.11");
    }

    #[test]
    fn link_specs_plain_and_renamed() {
        let config = Config::parse(
            r#"
            [virtualenv.myenv]
            link = ["foo", "bar:baz"]
            "#,
        )
        .unwrap();

        let venv = &config.virtualenvs["myenv"];
        assert_eq!(
            venv.link,
            vec![
                LinkSpec {
                    source: "foo".into(),
                    target: "foo".into(),
                },
                LinkSpec {
                    source: "bar".into(),
                    target: "baz".into(),
                },
            ]
        );
    }

    #[test]
    fn link_module_specs() {
        let config = Config::parse(
            r#"
            [virtualenv.myenv]
            link-module = ["jupyter", "ipython:ipy"]
            "#,
        )
        .unwrap();

        let venv = &config.virtualenvs["myenv"];
        assert_eq!(
            venv.link_module,
            vec![
                LinkSpec {
                    source: "jupyter".into(),
                    target: "jupyter".into(),
                },
                LinkSpec {
                    source: "ipython".into(),
                    target: "ipy".into(),
                },
            ]
        );
    }

    #[test]
    fn bundles_expand_into_install() {
        let config = Config::parse(
            r#"
            [bundle]
            dev = ["pytest", "ruff"]

            [virtualenv.myenv]
            install = ["mypackage"]
            install-bundle = ["dev"]
            "#,
        )
        .unwrap();

        assert_eq!(
            config.virtualenvs["myenv"].install,
            vec!["mypackage", "pytest", "ruff"],
        );
    }

    #[test]
    fn bundles_skip_duplicates() {
        let config = Config::parse(
            r#"
            [bundle]
            dev = ["pytest", "ruff"]

            [virtualenv.myenv]
            install = ["pytest"]
            install-bundle = ["dev"]
            "#,
        )
        .unwrap();

        assert_eq!(config.virtualenvs["myenv"].install, vec!["pytest", "ruff"],);
    }

    #[test]
    fn missing_bundle_is_an_error() {
        let err = Config::parse(
            r#"
            [virtualenv.myenv]
            install = ["foo"]
            install-bundle = ["nonexistent"]
            "#,
        )
        .unwrap_err();

        let msg = err.to_string();
        assert!(
            msg.contains("nonexistent"),
            "error should name the bundle: {msg}"
        );
        assert!(msg.contains("myenv"), "error should name the venv: {msg}");
    }

    #[test]
    fn duplicated_link_targets_across_venvs() {
        let err = Config::parse(
            r#"
            [virtualenv.a]
            link = ["foo"]

            [virtualenv.b]
            link = ["foo"]
            "#,
        )
        .unwrap_err();

        assert!(
            err.to_string().contains("foo"),
            "error should mention 'foo': {err}",
        );
    }

    #[test]
    fn duplicated_link_targets_across_link_and_module() {
        assert!(
            Config::parse(
                r#"
            [virtualenv.a]
            link = ["foo"]

            [virtualenv.b]
            link-module = ["bar:foo"]
            "#,
            )
            .is_err()
        );
    }

    #[test]
    fn duplicated_link_targets_within_same_venv() {
        assert!(
            Config::parse(
                r#"
            [virtualenv.a]
            link = ["foo", "bar:foo"]
            "#,
            )
            .is_err()
        );
    }

    #[test]
    fn duplicated_link_module_targets_within_same_venv() {
        assert!(
            Config::parse(
                r#"
            [virtualenv.a]
            link-module = ["foo", "bar:foo"]
            "#,
            )
            .is_err()
        );
    }

    #[test]
    fn duplicated_link_targets_via_rename() {
        assert!(
            Config::parse(
                r#"
            [virtualenv.a]
            link = ["foo"]

            [virtualenv.b]
            link = ["bar:foo"]
            "#,
            )
            .is_err()
        );
    }

    #[test]
    fn same_source_with_different_targets_is_fine() {
        let config = Config::parse(
            r#"
            [virtualenv.a]
            link = ["this:that", "this"]
            "#,
        )
        .unwrap();

        let venv = &config.virtualenvs["a"];
        assert_eq!(venv.link.len(), 2);
        assert_eq!(venv.link[0].target, "that");
        assert_eq!(venv.link[1].target, "this");
    }

    #[test]
    fn post_commands() {
        let config = Config::parse(
            r#"
            [virtualenv.myenv]
            post-commands = [["echo", "hello"], ["true"]]
            "#,
        )
        .unwrap();

        assert_eq!(
            config.virtualenvs["myenv"].post_commands,
            vec![vec!["echo", "hello"], vec!["true"]],
        );
    }

    #[test]
    fn requirements() {
        let config = Config::parse(
            r#"
            [virtualenv.myenv]
            requirements = ["requirements.txt"]
            "#,
        )
        .unwrap();

        assert_eq!(
            config.virtualenvs["myenv"].requirements,
            vec!["requirements.txt"],
        );
    }

    #[test]
    fn env_var_expansion_in_install() {
        // SAFETY: test-only, no other threads depend on this variable.
        unsafe { std::env::set_var("_VENVS_TEST_VAR", "expanded") };
        let config = Config::parse(
            r#"
            [virtualenv.myenv]
            install = ["$_VENVS_TEST_VAR"]
            "#,
        )
        .unwrap();

        assert_eq!(config.virtualenvs["myenv"].install, vec!["expanded"]);
        // SAFETY: test-only, no other threads depend on this variable.
        unsafe { std::env::remove_var("_VENVS_TEST_VAR") };
    }

    #[test]
    fn tilde_expansion_in_requirements() {
        let config = Config::parse(
            r#"
            [virtualenv.myenv]
            requirements = ["~/requirements.txt"]
            "#,
        )
        .unwrap();

        let home = dirs::home_dir().unwrap();
        assert_eq!(
            config.virtualenvs["myenv"].requirements,
            vec![home.join("requirements.txt").to_string_lossy().to_string()],
        );
    }

    #[test]
    fn multiple_venvs_sorted_by_name() {
        let config = Config::parse(
            r#"
            [virtualenv.zebra]
            [virtualenv.alpha]
            [virtualenv.middle]
            "#,
        )
        .unwrap();

        let names: Vec<_> = config.virtualenvs.keys().map(String::as_str).collect();
        assert_eq!(names, vec!["alpha", "middle", "zebra"]);
    }
}
