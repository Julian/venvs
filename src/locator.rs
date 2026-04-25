use std::path::{Path, PathBuf};

use anyhow::{Context, Result};

/// Locates virtualenvs from a common root directory.
pub struct Locator {
    pub root: PathBuf,
}

impl Locator {
    pub fn new(root: Option<PathBuf>) -> Result<Self> {
        let root = match root {
            Some(r) => r,
            None => default_root()?,
        };
        Ok(Self { root })
    }

    /// Resolve a virtualenv name to its directory path.
    pub fn for_name(&self, name: &str) -> PathBuf {
        self.root.join(normalize_name(name))
    }

    /// Find the virtualenv that would be associated with the given directory.
    pub fn for_directory(&self, directory: &Path) -> PathBuf {
        let basename = directory
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("unknown");
        self.for_name(basename)
    }

    /// Path to the config file.
    pub fn config_path(&self) -> PathBuf {
        self.root.join("virtualenvs.toml")
    }
}

/// Normalize a virtualenv name to match Python's behavior:
///
/// 1. Strip `.py` suffix or `python-` prefix (case-sensitive, on original)
/// 2. Lowercase
/// 3. Replace `-` with `_`
fn normalize_name(name: &str) -> String {
    let name = if let Some(stripped) = name.strip_suffix(".py") {
        stripped
    } else if let Some(stripped) = name.strip_prefix("python-") {
        stripped
    } else {
        name
    };
    name.to_lowercase().replace('-', "_")
}

fn default_root() -> Result<PathBuf> {
    if let Ok(workon_home) = std::env::var("WORKON_HOME") {
        return Ok(PathBuf::from(workon_home));
    }

    if cfg!(target_os = "macos") {
        let home = dirs::home_dir().context("could not determine home directory")?;
        Ok(home.join(".local/share/virtualenvs"))
    } else {
        dirs::data_dir()
            .map(|d| d.join("virtualenvs"))
            .context("could not determine data directory")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalize_lowercase() {
        assert_eq!(normalize_name("MyPackage"), "mypackage");
    }

    #[test]
    fn normalize_dashes_to_underscores() {
        assert_eq!(normalize_name("my-package"), "my_package");
    }

    #[test]
    fn normalize_strips_py_suffix() {
        assert_eq!(normalize_name("script.py"), "script");
    }

    #[test]
    fn normalize_py_suffix_is_case_sensitive() {
        // .PY should NOT be stripped (matches Python behavior).
        assert_eq!(normalize_name("script.PY"), "script.py");
    }

    #[test]
    fn normalize_strips_python_prefix() {
        assert_eq!(normalize_name("python-foo"), "foo");
    }

    #[test]
    fn normalize_python_prefix_is_case_sensitive() {
        // Python- should NOT be stripped (matches Python behavior).
        assert_eq!(normalize_name("Python-foo"), "python_foo");
    }

    #[test]
    fn normalize_combined() {
        assert_eq!(normalize_name("My-Package"), "my_package");
    }

    #[test]
    fn for_name_normalizes() {
        let locator = Locator {
            root: PathBuf::from("/tmp/venvs"),
        };
        assert_eq!(
            locator.for_name("My-Package"),
            PathBuf::from("/tmp/venvs/my_package"),
        );
    }

    #[test]
    fn for_directory_uses_basename() {
        let locator = Locator {
            root: PathBuf::from("/tmp/venvs"),
        };
        assert_eq!(
            locator.for_directory(Path::new("/home/user/projects/my-project")),
            PathBuf::from("/tmp/venvs/my_project"),
        );
    }
}
