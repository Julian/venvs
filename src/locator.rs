use std::path::{Component, Path, PathBuf};

use anyhow::{Context, Result, bail};

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
    pub fn for_directory(&self, directory: &Path) -> Result<PathBuf> {
        let basename = directory
            .file_name()
            .and_then(|n| n.to_str())
            .with_context(|| format!("no basename in {}", directory.display()))?;
        Ok(self.for_name(basename))
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
pub(crate) fn normalize_name(name: &str) -> String {
    let name = if let Some(stripped) = name.strip_suffix(".py") {
        stripped
    } else if let Some(stripped) = name.strip_prefix("python-") {
        stripped
    } else {
        name
    };
    name.to_lowercase().replace('-', "_")
}

/// Reject names that would normalize to anything other than a single
/// safe path component. Without this, a config or state entry like
/// `"../etc"` would let `for_name` produce a path that escapes `root`,
/// and any subsequent filesystem op (create, remove) would touch files
/// outside the venvs root.
pub(crate) fn validate_name(name: &str) -> Result<()> {
    let normalized = normalize_name(name);
    if normalized.is_empty() {
        bail!("invalid virtualenv name {name:?}: empty after normalization");
    }
    if normalized.chars().any(|c| c == '\0' || c.is_control()) {
        bail!("invalid virtualenv name {name:?}: contains a control character");
    }
    if normalized.contains('/') || normalized.contains('\\') {
        bail!("invalid virtualenv name {name:?}: contains a path separator");
    }
    let mut comps = Path::new(&normalized).components();
    match (comps.next(), comps.next()) {
        (Some(Component::Normal(_)), None) => Ok(()),
        _ => bail!(
            "invalid virtualenv name {name:?}: must be a single path component, \
             not {normalized:?}"
        ),
    }
}

fn default_root() -> Result<PathBuf> {
    if let Ok(workon_home) = std::env::var("WORKON_HOME") {
        return Ok(PathBuf::from(shellexpand::tilde(&workon_home).into_owned()));
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
            locator
                .for_directory(Path::new("/home/user/projects/my-project"))
                .unwrap(),
            PathBuf::from("/tmp/venvs/my_project"),
        );
    }

    #[test]
    fn for_directory_errors_when_no_basename() {
        let locator = Locator {
            root: PathBuf::from("/tmp/venvs"),
        };
        assert!(locator.for_directory(Path::new("/")).is_err());
    }

    #[test]
    fn validate_name_accepts_simple() {
        assert!(validate_name("my-project").is_ok());
        assert!(validate_name("MyProject").is_ok());
        assert!(validate_name("a").is_ok());
    }

    #[test]
    fn validate_name_rejects_path_separator() {
        assert!(validate_name("foo/bar").is_err());
        assert!(validate_name("/foo").is_err());
        assert!(validate_name("foo/").is_err());
    }

    #[test]
    fn validate_name_rejects_parent_dir() {
        assert!(validate_name("..").is_err());
        assert!(validate_name("../foo").is_err());
        assert!(validate_name("foo/../bar").is_err());
    }

    #[test]
    fn validate_name_rejects_current_dir() {
        assert!(validate_name(".").is_err());
    }

    #[test]
    fn validate_name_rejects_empty() {
        assert!(validate_name("").is_err());
    }

    #[test]
    fn validate_name_rejects_null_byte() {
        assert!(validate_name("foo\0bar").is_err());
    }

    #[test]
    fn validate_name_rejects_newline() {
        assert!(validate_name("foo\nbar").is_err());
    }
}
