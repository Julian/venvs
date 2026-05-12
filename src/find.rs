use std::env;
use std::path::PathBuf;
use std::process::ExitCode;

use anyhow::{Context, Result};
use clap::Subcommand;

use crate::locator::{Locator, validate_name};

#[derive(Subcommand)]
pub enum FindCommand {
    /// Find the virtualenv given the project's name.
    Name {
        name: String,
        binary: Option<String>,
    },
    /// Find the virtualenv given the project's path.
    Directory {
        directory: Option<PathBuf>,
        binary: Option<String>,
    },
}

pub fn run(
    locator: &Locator,
    command: Option<FindCommand>,
    existing_only: bool,
) -> Result<ExitCode> {
    let (venv_dir, binary) = match command {
        None => {
            println!("{}", locator.root.display());
            return Ok(ExitCode::SUCCESS);
        }
        Some(FindCommand::Name { name, binary }) => {
            validate_name(&name)?;
            (resolve_name_with_dev_fallback(locator, &name), binary)
        }
        Some(FindCommand::Directory { directory, binary }) => {
            let dir = match directory {
                Some(d) => d,
                None => env::current_dir().context("getting current directory")?,
            };
            let venv = locator.for_directory(&dir)?;
            // for_directory already pulled out the basename, but a basename
            // like ".." would still let the resulting path escape the root.
            let basename = venv
                .file_name()
                .and_then(|n| n.to_str())
                .context("derived venv path has no basename")?;
            validate_name(basename)?;
            (venv, binary)
        }
    };

    if existing_only && !venv_dir.exists() {
        return Ok(ExitCode::FAILURE);
    }

    match binary {
        Some(bin) => {
            println!("{}", venv_dir.join("bin").join(bin).display());
        }
        None => {
            println!("{}", venv_dir.display());
        }
    }

    Ok(ExitCode::SUCCESS)
}

/// Resolve `name` to a venv path, trying `<name>` first and falling back to
/// `<name>-dev` when the bare name doesn't exist on disk. The `-dev` suffix
/// is a disk-layout detail of `[dev.X]` venvs that users shouldn't have to
/// know about — when only the dev variant exists, `venvs find name foo`
/// should find it.
fn resolve_name_with_dev_fallback(locator: &Locator, name: &str) -> PathBuf {
    let direct = locator.for_name(name);
    if direct.exists() {
        return direct;
    }
    let with_dev = format!("{name}-dev");
    let dev_path = locator.for_name(&with_dev);
    if dev_path.exists() {
        return dev_path;
    }
    direct
}

#[cfg(test)]
mod tests {
    use std::fs;
    use tempfile::TempDir;

    use super::*;

    fn make_locator() -> (TempDir, Locator) {
        let dir = TempDir::new().unwrap();
        let locator = Locator {
            root: dir.path().to_path_buf(),
        };
        (dir, locator)
    }

    #[test]
    fn fallback_returns_direct_when_it_exists() {
        let (_dir, locator) = make_locator();
        fs::create_dir(locator.for_name("foo")).unwrap();
        let path = resolve_name_with_dev_fallback(&locator, "foo");
        assert_eq!(path, locator.for_name("foo"));
    }

    #[test]
    fn fallback_routes_to_dev_when_only_dev_exists() {
        let (_dir, locator) = make_locator();
        fs::create_dir(locator.for_name("foo-dev")).unwrap();
        let path = resolve_name_with_dev_fallback(&locator, "foo");
        assert_eq!(path, locator.for_name("foo-dev"));
    }

    #[test]
    fn fallback_prefers_direct_when_both_exist() {
        let (_dir, locator) = make_locator();
        fs::create_dir(locator.for_name("foo")).unwrap();
        fs::create_dir(locator.for_name("foo-dev")).unwrap();
        let path = resolve_name_with_dev_fallback(&locator, "foo");
        assert_eq!(path, locator.for_name("foo"));
    }

    #[test]
    fn fallback_returns_direct_when_neither_exists() {
        let (_dir, locator) = make_locator();
        let path = resolve_name_with_dev_fallback(&locator, "foo");
        assert_eq!(path, locator.for_name("foo"));
    }

    #[test]
    fn fallback_with_explicit_dev_suffix_finds_directly() {
        let (_dir, locator) = make_locator();
        fs::create_dir(locator.for_name("foo-dev")).unwrap();
        let path = resolve_name_with_dev_fallback(&locator, "foo-dev");
        assert_eq!(path, locator.for_name("foo-dev"));
    }
}
