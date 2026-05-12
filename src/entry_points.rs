use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};

/// Discover the console/GUI scripts that the given package's wheel
/// declared, by parsing its installed `entry_points.txt`.
///
/// Returns an empty list if the package has no entry points at all (some
/// libraries are import-only and ship no scripts). Errors if the package
/// is not installed in the venv.
pub fn discover_scripts(venv_dir: &Path, package: &str) -> Result<Vec<String>> {
    let site_packages = find_site_packages(venv_dir)?;
    let dist_info = find_dist_info(&site_packages, package)?.with_context(|| {
        format!(
            "no installed dist-info for package {package:?} in {}",
            site_packages.display(),
        )
    })?;
    let ep_path = dist_info.join("entry_points.txt");
    let content = match fs::read_to_string(&ep_path) {
        Ok(c) => c,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Vec::new()),
        Err(e) => return Err(e).with_context(|| format!("reading {}", ep_path.display())),
    };
    Ok(parse_scripts(&content))
}

/// Parse the `[console_scripts]` and `[gui_scripts]` sections of an
/// `entry_points.txt` (an INI-shaped file), returning the script names
/// (the keys before `=`).
fn parse_scripts(content: &str) -> Vec<String> {
    let mut current: Option<&str> = None;
    let mut scripts = Vec::new();
    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') || line.starts_with(';') {
            continue;
        }
        if let Some(name) = line.strip_prefix('[').and_then(|s| s.strip_suffix(']')) {
            current = Some(name.trim());
            continue;
        }
        if matches!(current, Some("console_scripts" | "gui_scripts"))
            && let Some((key, _)) = line.split_once('=')
        {
            scripts.push(key.trim().to_string());
        }
    }
    scripts
}

fn find_site_packages(venv_dir: &Path) -> Result<PathBuf> {
    let lib = venv_dir.join("lib");
    let mut matches = Vec::new();
    for entry in fs::read_dir(&lib).with_context(|| format!("reading {}", lib.display()))? {
        let entry = entry?;
        if entry.file_name().to_string_lossy().starts_with("python") {
            let sp = entry.path().join("site-packages");
            if sp.is_dir() {
                matches.push(sp);
            }
        }
    }
    match matches.len() {
        0 => bail!("no python*/site-packages directory under {}", lib.display()),
        1 => Ok(matches.pop().unwrap()),
        _ => bail!(
            "multiple python lib directories under {}: {matches:?}",
            lib.display(),
        ),
    }
}

fn find_dist_info(site_packages: &Path, package: &str) -> Result<Option<PathBuf>> {
    let target = canonicalize(package);
    for entry in fs::read_dir(site_packages)
        .with_context(|| format!("reading {}", site_packages.display()))?
    {
        let entry = entry?;
        let name = entry.file_name();
        let name_str = name.to_string_lossy();
        let Some(prefix) = name_str.strip_suffix(".dist-info") else {
            continue;
        };
        let Some((pkg, _version)) = prefix.rsplit_once('-') else {
            continue;
        };
        if canonicalize(pkg) == target {
            return Ok(Some(entry.path()));
        }
    }
    Ok(None)
}

/// PEP 503 canonical project name: lowercase, with runs of `.`, `-`, `_`
/// collapsed to a single `-`.
fn canonicalize(name: &str) -> String {
    let mut out = String::with_capacity(name.len());
    let mut prev_dash = false;
    for c in name.chars() {
        if matches!(c, '.' | '-' | '_') {
            if !prev_dash && !out.is_empty() {
                out.push('-');
                prev_dash = true;
            }
        } else {
            out.push(c.to_ascii_lowercase());
            prev_dash = false;
        }
    }
    if out.ends_with('-') {
        out.pop();
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_console_scripts_basic() {
        let scripts = parse_scripts(
            "\
[console_scripts]
black = black:patched_main
blackd = blackd:main

[other_section]
ignored = ignored:main
",
        );
        assert_eq!(scripts, vec!["black", "blackd"]);
    }

    #[test]
    fn parse_includes_gui_scripts() {
        let scripts = parse_scripts(
            "\
[gui_scripts]
viewer = pkg:gui

[console_scripts]
cli = pkg:main
",
        );
        assert_eq!(scripts, vec!["viewer", "cli"]);
    }

    #[test]
    fn parse_ignores_comments_and_blanks() {
        let scripts = parse_scripts(
            "\
# top-level comment
; also a comment

[console_scripts]
# inside-section comment
foo = pkg:main
",
        );
        assert_eq!(scripts, vec!["foo"]);
    }

    #[test]
    fn parse_empty_returns_empty() {
        assert!(parse_scripts("").is_empty());
        assert!(parse_scripts("\n\n\n").is_empty());
    }

    #[test]
    fn canonicalize_matches_pep_503() {
        assert_eq!(canonicalize("requests"), "requests");
        assert_eq!(canonicalize("Django"), "django");
        assert_eq!(canonicalize("python-dateutil"), "python-dateutil");
        assert_eq!(canonicalize("python_dateutil"), "python-dateutil");
        assert_eq!(canonicalize("Python.Date.Util"), "python-date-util");
        assert_eq!(canonicalize("foo___bar---baz"), "foo-bar-baz");
        assert_eq!(canonicalize("_leading"), "leading");
        assert_eq!(canonicalize("trailing_"), "trailing");
    }

    fn make_dist_info(site_packages: &Path, name: &str, version: &str, entry_points: Option<&str>) {
        let dir = site_packages.join(format!("{name}-{version}.dist-info"));
        fs::create_dir_all(&dir).unwrap();
        if let Some(content) = entry_points {
            fs::write(dir.join("entry_points.txt"), content).unwrap();
        }
    }

    fn make_venv(version: &str) -> tempfile::TempDir {
        let dir = tempfile::tempdir().unwrap();
        let sp = dir
            .path()
            .join("lib")
            .join(format!("python{version}"))
            .join("site-packages");
        fs::create_dir_all(&sp).unwrap();
        dir
    }

    fn site_packages(venv: &tempfile::TempDir) -> PathBuf {
        find_site_packages(venv.path()).unwrap()
    }

    #[test]
    fn discover_finds_scripts_via_canonicalized_match() {
        let venv = make_venv("3.12");
        make_dist_info(
            &site_packages(&venv),
            "python_dateutil",
            "2.8.2",
            Some("[console_scripts]\ndateutil = mod:main\n"),
        );

        // PyPI name `python-dateutil` resolves to dist-info `python_dateutil-*`.
        let scripts = discover_scripts(venv.path(), "python-dateutil").unwrap();
        assert_eq!(scripts, vec!["dateutil"]);
    }

    #[test]
    fn discover_returns_empty_when_no_entry_points_file() {
        let venv = make_venv("3.12");
        make_dist_info(&site_packages(&venv), "requests", "2.31.0", None);
        assert!(
            discover_scripts(venv.path(), "requests")
                .unwrap()
                .is_empty()
        );
    }

    #[test]
    fn discover_errors_when_package_not_installed() {
        let venv = make_venv("3.12");
        let err = discover_scripts(venv.path(), "missing").unwrap_err();
        assert!(format!("{err:#}").contains("missing"));
    }

    #[test]
    fn discover_errors_when_no_python_lib_dir() {
        let dir = tempfile::tempdir().unwrap();
        fs::create_dir_all(dir.path().join("lib")).unwrap();
        assert!(discover_scripts(dir.path(), "foo").is_err());
    }
}
