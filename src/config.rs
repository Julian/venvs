use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::Path;

use anyhow::{Context, Result, bail};
use serde::{Deserialize, Serialize};

use crate::locator::{normalize_name, validate_name};

/// Raw TOML config as deserialized from virtualenvs.toml.
#[derive(Debug, Default, Deserialize)]
#[serde(default)]
struct RawConfig {
    bundle: BTreeMap<String, Vec<String>>,
    venv: BTreeMap<String, RawVirtualEnvConfig>,
    virtualenv: BTreeMap<String, RawVirtualEnvConfig>,
    tool: BTreeMap<String, RawToolConfig>,
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

/// `[tool.X]` is sugar for "install the package `X` (with optional extras
/// and companion packages) and link its scripts." Unlike [`RawVirtualEnvConfig`],
/// it has no `requirements` (use `[venv.X]` if you need that), and `install`
/// here means *additional* packages (`uv tool install foo --with bar`-style),
/// not the primary package — the primary package is always the venv name.
#[derive(Debug, Default, Deserialize)]
#[serde(default, deny_unknown_fields)]
struct RawToolConfig {
    python: Option<String>,
    extras: Vec<String>,
    install: Vec<String>,
    #[serde(rename = "install-bundle")]
    install_bundle: Vec<String>,
    link: Option<Vec<String>>,
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
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default)]
pub struct ResolvedVirtualEnv {
    pub name: String,
    pub python: String,
    pub install: Vec<String>,
    pub requirements: Vec<String>,
    pub link: Vec<LinkSpec>,
    pub link_module: Vec<LinkSpec>,
    pub post_commands: Vec<Vec<String>>,
    /// If set, after install, console scripts declared by this package are
    /// discovered and added to the link list. Used by `[tool.X]` when the
    /// user didn't specify `link` explicitly.
    pub auto_link_package: Option<String>,
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
        let mut virtualenvs: BTreeMap<String, ResolvedVirtualEnv> = BTreeMap::new();
        let mut declared_in: BTreeMap<String, &'static str> = BTreeMap::new();

        for (table, entries) in [("venv", &raw.venv), ("virtualenv", &raw.virtualenv)] {
            for (name, raw_venv) in entries {
                validate_name(name).context("invalid venv name")?;
                check_uniqueness(name, table, &mut declared_in)?;
                let source = format!("[{table}.{name}]");
                virtualenvs.insert(
                    name.clone(),
                    resolve_venv(name, &source, raw_venv, &raw.bundle)?,
                );
            }
        }
        for (name, raw_tool) in &raw.tool {
            validate_name(name).context("invalid venv name")?;
            check_uniqueness(name, "tool", &mut declared_in)?;
            let source = format!("[tool.{name}]");
            virtualenvs.insert(
                name.clone(),
                resolve_tool(name, &source, raw_tool, &raw.bundle)?,
            );
        }

        check_for_normalized_name_collisions(&virtualenvs)?;
        check_for_duplicated_links(&virtualenvs)?;

        Ok(Config { virtualenvs })
    }
}

fn check_uniqueness(
    name: &str,
    table: &'static str,
    declared_in: &mut BTreeMap<String, &'static str>,
) -> Result<()> {
    if let Some(prev) = declared_in.get(name) {
        bail!(
            "venv {name:?} is declared in both [{prev}.{name}] and [{table}.{name}] \
             — pick one"
        );
    }
    declared_in.insert(name.to_string(), table);
    Ok(())
}

fn resolve_tool(
    name: &str,
    source: &str,
    raw: &RawToolConfig,
    bundles: &BTreeMap<String, Vec<String>>,
) -> Result<ResolvedVirtualEnv> {
    for extra in &raw.extras {
        validate_extra(extra).with_context(|| format!("invalid extra in {source}"))?;
    }

    let primary_spec = if raw.extras.is_empty() {
        name.to_string()
    } else {
        format!("{name}[{}]", raw.extras.join(","))
    };

    let mut install = vec![primary_spec];
    for companion in &raw.install {
        install.push(expand(companion)?);
    }
    expand_bundles_into(&mut install, &raw.install_bundle, bundles, source)?;
    validate_install(&install, source)?;

    let (link, auto_link_package) = match &raw.link {
        Some(specs) => (parse_link_specs(specs), None),
        None => (Vec::new(), Some(name.to_string())),
    };
    validate_link_specs(&link, source)?;

    let link_module = parse_link_specs(&raw.link_module);
    validate_link_module_specs(&link_module, source)?;

    Ok(ResolvedVirtualEnv {
        name: name.to_string(),
        python: raw.python.clone().unwrap_or_else(|| "python3".to_string()),
        install,
        requirements: Vec::new(),
        link,
        link_module,
        post_commands: raw.post_commands.clone(),
        auto_link_package,
    })
}

fn resolve_venv(
    name: &str,
    source: &str,
    raw: &RawVirtualEnvConfig,
    bundles: &BTreeMap<String, Vec<String>>,
) -> Result<ResolvedVirtualEnv> {
    let mut install: Vec<String> = raw
        .install
        .iter()
        .map(|s| expand(s))
        .collect::<Result<_>>()?;
    expand_bundles_into(&mut install, &raw.install_bundle, bundles, source)?;
    validate_install(&install, source)?;

    let requirements: Vec<String> = raw
        .requirements
        .iter()
        .map(|s| expand(s))
        .collect::<Result<_>>()?;
    for req in &requirements {
        validate_package_arg(req)
            .with_context(|| format!("invalid requirements entry in {source}"))?;
    }

    let link = parse_link_specs(&raw.link);
    validate_link_specs(&link, source)?;

    let link_module = parse_link_specs(&raw.link_module);
    validate_link_module_specs(&link_module, source)?;

    Ok(ResolvedVirtualEnv {
        name: name.to_string(),
        python: raw.python.clone().unwrap_or_else(|| "python3".to_string()),
        install,
        requirements,
        link,
        link_module,
        post_commands: raw.post_commands.clone(),
        auto_link_package: None,
    })
}

fn expand_bundles_into(
    install: &mut Vec<String>,
    bundle_names: &[String],
    bundles: &BTreeMap<String, Vec<String>>,
    source: &str,
) -> Result<()> {
    for bundle_name in bundle_names {
        let bundle = bundles
            .get(bundle_name)
            .with_context(|| format!("{source} references unknown bundle {bundle_name:?}"))?;
        for package in bundle {
            let expanded = expand(package)?;
            if !install.contains(&expanded) {
                install.push(expanded);
            }
        }
    }
    Ok(())
}

fn validate_install(install: &[String], source: &str) -> Result<()> {
    for package in install {
        validate_package_arg(package)
            .with_context(|| format!("invalid install entry in {source}"))?;
    }
    Ok(())
}

fn validate_link_specs(specs: &[LinkSpec], source: &str) -> Result<()> {
    for spec in specs {
        validate_filename(&spec.source)
            .with_context(|| format!("invalid link source in {source}"))?;
        validate_filename(&spec.target)
            .with_context(|| format!("invalid link target in {source}"))?;
    }
    Ok(())
}

fn validate_link_module_specs(specs: &[LinkSpec], source: &str) -> Result<()> {
    for spec in specs {
        validate_python_module(&spec.source)
            .with_context(|| format!("invalid link-module source in {source}"))?;
        validate_filename(&spec.target)
            .with_context(|| format!("invalid link-module target in {source}"))?;
    }
    Ok(())
}

/// PEP 508 extra names: ASCII alphanumeric plus `-`, `_`, `.`.
fn validate_extra(s: &str) -> Result<()> {
    if s.is_empty() {
        bail!("empty extra");
    }
    if !s
        .chars()
        .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_' || c == '.')
    {
        bail!("invalid extra {s:?}");
    }
    Ok(())
}

/// Reject anything that `uv pip install` would parse as a flag rather than
/// as a positional package argument. Without this, an entry like
/// `--index-url=http://attacker/` silently redirects the install.
fn validate_package_arg(s: &str) -> Result<()> {
    if s.is_empty() {
        bail!("empty package/requirement entry");
    }
    if s.starts_with('-') {
        bail!("entry {s:?} starts with '-' (would be parsed as a flag by uv)");
    }
    Ok(())
}

/// A link source is looked up in the venv's `bin/` and a link target lands
/// in the link dir. Either with `..` or `/` would let the config reach
/// outside those directories.
fn validate_filename(s: &str) -> Result<()> {
    if s.is_empty() {
        bail!("empty filename");
    }
    if s == "." || s == ".." {
        bail!("filename {s:?} is a path traversal");
    }
    if s.contains('/') || s.contains('\\') || s.contains('\0') {
        bail!("filename {s:?} contains a path separator or null byte");
    }
    if s.chars().any(char::is_control) {
        bail!("filename {s:?} contains a control character");
    }
    Ok(())
}

/// Validate that `s` is a Python module identifier (`a.b.c`). The string
/// is interpolated verbatim into a generated Python wrapper, so anything
/// other than a safe identifier is potential code injection.
fn validate_python_module(s: &str) -> Result<()> {
    if s.is_empty() {
        bail!("empty module name");
    }
    let valid = s.split('.').all(|part| {
        let mut chars = part.chars();
        match chars.next() {
            Some(c) if c.is_ascii_alphabetic() || c == '_' => {
                chars.all(|c| c.is_ascii_alphanumeric() || c == '_')
            }
            _ => false,
        }
    });
    if !valid {
        bail!("{s:?} is not a valid Python module name");
    }
    Ok(())
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

fn check_for_normalized_name_collisions(
    virtualenvs: &BTreeMap<String, ResolvedVirtualEnv>,
) -> Result<()> {
    let mut by_normalized: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for name in virtualenvs.keys() {
        by_normalized
            .entry(normalize_name(name))
            .or_default()
            .push(name.clone());
    }
    let collisions: Vec<_> = by_normalized
        .into_iter()
        .filter(|(_, names)| names.len() > 1)
        .collect();
    if !collisions.is_empty() {
        let mut details = Vec::new();
        for (normalized, names) in collisions {
            details.push(format!("{} -> {normalized}", names.join(", ")));
        }
        bail!(
            "virtualenv names collide after normalization: {}",
            details.join("; ")
        );
    }
    Ok(())
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
    fn venv_table_is_equivalent_to_virtualenv_table() {
        let config = Config::parse(
            r#"
            [venv.myenv]
            install = ["requests"]
            "#,
        )
        .unwrap();

        let venv = &config.virtualenvs["myenv"];
        assert_eq!(venv.name, "myenv");
        assert_eq!(venv.install, vec!["requests"]);
    }

    #[test]
    fn venv_and_virtualenv_tables_coexist() {
        let config = Config::parse(
            r#"
            [venv.alpha]
            install = ["a"]
            [virtualenv.beta]
            install = ["b"]
            "#,
        )
        .unwrap();

        assert_eq!(config.virtualenvs["alpha"].install, vec!["a"]);
        assert_eq!(config.virtualenvs["beta"].install, vec!["b"]);
    }

    #[test]
    fn same_name_in_both_tables_is_rejected() {
        let err = Config::parse(
            r#"
            [venv.shared]
            install = ["a"]
            [virtualenv.shared]
            install = ["b"]
            "#,
        )
        .unwrap_err();
        let msg = format!("{err:#}");
        assert!(msg.contains("shared"), "error should name the venv: {msg}");
        assert!(
            msg.contains("[venv.") && msg.contains("[virtualenv."),
            "error should name both tables: {msg}",
        );
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
        // Use HOME (always set on the platforms we support) instead of
        // mutating the process environment, which is unsafe under parallel
        // tests.
        let home = std::env::var("HOME").expect("HOME must be set");
        let config = Config::parse(
            r#"
            [virtualenv.myenv]
            install = ["$HOME"]
            "#,
        )
        .unwrap();

        assert_eq!(config.virtualenvs["myenv"].install, vec![home]);
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

    #[test]
    fn rejects_path_traversal_venv_name() {
        let err = Config::parse(
            r#"
            [virtualenv."../etc"]
            "#,
        )
        .unwrap_err();
        assert!(
            format!("{err:#}").contains("../etc"),
            "error should name the bad name: {err:#}",
        );
    }

    #[test]
    fn rejects_slash_in_venv_name() {
        assert!(
            Config::parse(
                r#"
                [virtualenv."foo/bar"]
                "#,
            )
            .is_err()
        );
    }

    #[test]
    fn rejects_normalized_name_collisions() {
        let err = Config::parse(
            r#"
            [virtualenv.foo-bar]
            [virtualenv.foo_bar]
            "#,
        )
        .unwrap_err();
        let msg = format!("{err:#}");
        assert!(
            msg.contains("foo_bar"),
            "error should name the collision: {msg}"
        );
    }

    #[test]
    fn rejects_install_entry_starting_with_dash() {
        let err = Config::parse(
            r#"
            [virtualenv.myenv]
            install = ["--index-url=http://attacker"]
            "#,
        )
        .unwrap_err();
        assert!(format!("{err:#}").contains("'-'"));
    }

    #[test]
    fn rejects_requirements_entry_starting_with_dash() {
        assert!(
            Config::parse(
                r#"
                [virtualenv.myenv]
                requirements = ["-rother.txt"]
                "#,
            )
            .is_err()
        );
    }

    #[test]
    fn rejects_install_via_bundle_starting_with_dash() {
        assert!(
            Config::parse(
                r#"
                [bundle]
                bad = ["--index-url=http://attacker"]
                [virtualenv.myenv]
                install-bundle = ["bad"]
                "#,
            )
            .is_err()
        );
    }

    #[test]
    fn rejects_link_source_with_path_separator() {
        assert!(
            Config::parse(
                r#"
                [virtualenv.myenv]
                link = ["../bad:tool"]
                "#,
            )
            .is_err()
        );
    }

    #[test]
    fn rejects_link_target_with_path_separator() {
        assert!(
            Config::parse(
                r#"
                [virtualenv.myenv]
                link = ["tool:../../usr/local/bin/sudo"]
                "#,
            )
            .is_err()
        );
    }

    #[test]
    fn rejects_link_module_target_with_path_separator() {
        assert!(
            Config::parse(
                r#"
                [virtualenv.myenv]
                link-module = ["mymod:../evil"]
                "#,
            )
            .is_err()
        );
    }

    #[test]
    fn rejects_link_module_source_with_injection() {
        let err = Config::parse(
            r#"
            [virtualenv.myenv]
            link-module = ["foo\"); __import__(\"os\").system(\"x\"); (\""]
            "#,
        )
        .unwrap_err();
        assert!(format!("{err:#}").contains("Python module"));
    }

    #[test]
    fn accepts_dotted_python_module() {
        let config = Config::parse(
            r#"
            [virtualenv.myenv]
            link-module = ["pkg.sub.mod:tool"]
            "#,
        )
        .unwrap();
        assert_eq!(
            config.virtualenvs["myenv"].link_module[0].source,
            "pkg.sub.mod"
        );
    }

    #[test]
    fn rejects_link_module_source_starting_with_digit() {
        assert!(
            Config::parse(
                r#"
                [virtualenv.myenv]
                link-module = ["1foo:tool"]
                "#,
            )
            .is_err()
        );
    }

    #[test]
    fn tool_table_defaults_to_installing_and_auto_linking_by_name() {
        let config = Config::parse(
            r#"
            [tool.black]
            "#,
        )
        .unwrap();

        let venv = &config.virtualenvs["black"];
        assert_eq!(venv.install, vec!["black"]);
        assert_eq!(venv.requirements, Vec::<String>::new());
        assert!(
            venv.link.is_empty(),
            "explicit link should be empty when auto-linking",
        );
        assert_eq!(venv.auto_link_package.as_deref(), Some("black"));
    }

    #[test]
    fn tool_table_extras_bake_into_primary_spec() {
        let config = Config::parse(
            r#"
            [tool.jsonschema]
            extras = ["format", "cli"]
            "#,
        )
        .unwrap();

        assert_eq!(
            config.virtualenvs["jsonschema"].install,
            vec!["jsonschema[format,cli]"]
        );
    }

    #[test]
    fn tool_table_install_is_additional_companions() {
        let config = Config::parse(
            r#"
            [tool.jupyter]
            install = ["jupyterlab", "ipywidgets"]
            "#,
        )
        .unwrap();

        let venv = &config.virtualenvs["jupyter"];
        assert_eq!(venv.install, vec!["jupyter", "jupyterlab", "ipywidgets"]);
        // No explicit link → auto-link, only from the primary package.
        assert!(venv.link.is_empty());
        assert_eq!(venv.auto_link_package.as_deref(), Some("jupyter"));
    }

    #[test]
    fn tool_table_explicit_link_overrides_auto() {
        let config = Config::parse(
            r#"
            [tool.jupyter]
            install = ["jupyterlab"]
            link = ["jupyter", "jupyter-lab"]
            "#,
        )
        .unwrap();

        let venv = &config.virtualenvs["jupyter"];
        let targets: Vec<_> = venv.link.iter().map(|l| l.target.as_str()).collect();
        assert_eq!(targets, vec!["jupyter", "jupyter-lab"]);
        assert!(
            venv.auto_link_package.is_none(),
            "explicit link should disable auto-link",
        );
    }

    #[test]
    fn tool_table_empty_explicit_link_disables_auto_link() {
        let config = Config::parse(
            r#"
            [tool.thing]
            link = []
            "#,
        )
        .unwrap();
        let venv = &config.virtualenvs["thing"];
        assert!(venv.link.is_empty());
        assert!(venv.auto_link_package.is_none());
    }

    #[test]
    fn tool_table_rejects_disallowed_keys() {
        for key in ["requirements", "project", "sync", "editable"] {
            let toml = format!("[tool.foo]\n{key} = \"x\"\n");
            let err = Config::parse(&toml).unwrap_err();
            let msg = format!("{err:#}");
            assert!(
                msg.contains("unknown field") || msg.contains(key),
                "expected rejection of {key}: {msg}",
            );
        }
    }

    #[test]
    fn tool_table_install_bundle_companions_skip_dup_of_primary() {
        let config = Config::parse(
            r#"
            [bundle]
            extras = ["black", "ruff"]

            [tool.black]
            install-bundle = ["extras"]
            "#,
        )
        .unwrap();

        assert_eq!(config.virtualenvs["black"].install, vec!["black", "ruff"]);
    }

    #[test]
    fn tool_and_venv_with_same_name_is_rejected() {
        let err = Config::parse(
            r#"
            [venv.foo]
            [tool.foo]
            "#,
        )
        .unwrap_err();
        let msg = format!("{err:#}");
        assert!(msg.contains("foo"), "should name the venv: {msg}");
        assert!(msg.contains("[venv.") && msg.contains("[tool."));
    }

    #[test]
    fn tool_table_rejects_dash_prefixed_companions() {
        let err = Config::parse(
            r#"
            [tool.foo]
            install = ["--index-url=http://attacker"]
            "#,
        )
        .unwrap_err();
        assert!(format!("{err:#}").contains("'-'"));
    }

    #[test]
    fn tool_table_custom_python() {
        let config = Config::parse(
            r#"
            [tool.black]
            python = "python3.12"
            "#,
        )
        .unwrap();
        assert_eq!(config.virtualenvs["black"].python, "python3.12");
    }

    #[test]
    fn tool_table_post_commands() {
        let config = Config::parse(
            r#"
            [tool.black]
            post-commands = [["echo", "done"]]
            "#,
        )
        .unwrap();
        assert_eq!(
            config.virtualenvs["black"].post_commands,
            vec![vec!["echo", "done"]]
        );
    }

    #[test]
    fn tool_table_rejects_invalid_extras() {
        for bad in ["bad extra", "with/slash", ""] {
            let toml = format!("[tool.foo]\nextras = [{:?}]\n", bad);
            assert!(Config::parse(&toml).is_err(), "should reject extra {bad:?}",);
        }
    }
}
