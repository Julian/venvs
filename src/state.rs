use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};

use crate::config::ResolvedVirtualEnv;
use crate::locator::validate_name;

/// State for a single managed virtualenv.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct VenvState {
    pub config: ResolvedVirtualEnv,
    pub sys_version: String,
    /// Absolute paths of symlinks/wrappers created in the link dir.
    pub links: Vec<PathBuf>,
}

/// Central state tracking all managed virtualenvs.
#[derive(Debug, Default, Serialize, Deserialize)]
pub struct ManagedState {
    pub venvs: BTreeMap<String, VenvState>,
}

impl ManagedState {
    /// Load state from disk, returning default if the file doesn't exist.
    ///
    /// Names are revalidated on load: a tampered or hand-edited
    /// `managed.json` whose keys contain `..`/`/` would otherwise let
    /// later `for_name(...)` calls escape the venvs root.
    pub fn load(path: &Path) -> Result<Self> {
        let state: Self = match fs::read_to_string(path) {
            Ok(contents) => serde_json::from_str(&contents)
                .with_context(|| format!("parsing {}", path.display()))?,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Self::default()),
            Err(e) => return Err(e).with_context(|| format!("reading {}", path.display())),
        };
        for name in state.venvs.keys() {
            validate_name(name)
                .with_context(|| format!("invalid venv name in {}", path.display()))?;
        }
        Ok(state)
    }

    /// Persist state to disk atomically (creates parent directories as needed).
    ///
    /// Writes to a sibling temp file, then renames over the target. A crash
    /// mid-write leaves the previous file intact rather than a half-written
    /// JSON blob.
    pub fn save(&self, path: &Path) -> Result<()> {
        let contents = serde_json::to_string_pretty(self).context("serializing state")?;
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)
                .with_context(|| format!("creating directory {}", parent.display()))?;
        }
        let tmp = path.with_extension("json.tmp");
        fs::write(&tmp, contents).with_context(|| format!("writing {}", tmp.display()))?;
        fs::rename(&tmp, path)
            .with_context(|| format!("renaming {} -> {}", tmp.display(), path.display()))
    }

    /// Find orphaned venv names: present in state but absent from config.
    pub fn orphaned_names(&self, current_names: &BTreeSet<String>) -> Vec<String> {
        self.venvs
            .keys()
            .filter(|name| !current_names.contains(*name))
            .cloned()
            .collect()
    }

    /// Check whether a venv needs to be recreated.
    pub fn needs_update(
        &self,
        name: &str,
        resolved: &ResolvedVirtualEnv,
        sys_version: &str,
    ) -> bool {
        match self.venvs.get(name) {
            Some(existing) => existing.config != *resolved || existing.sys_version != sys_version,
            None => true,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::LinkSpec;

    fn sample_venv(name: &str) -> ResolvedVirtualEnv {
        ResolvedVirtualEnv {
            name: name.to_string(),
            python: "python3".to_string(),
            install: vec!["requests".to_string()],
            requirements: vec![],
            link: vec![LinkSpec {
                source: "http".into(),
                target: "http".into(),
            }],
            link_module: vec![],
            post_commands: vec![],
        }
    }

    fn sample_state(name: &str) -> VenvState {
        VenvState {
            config: sample_venv(name),
            sys_version: "Python 3.12.0".to_string(),
            links: vec![],
        }
    }

    #[test]
    fn needs_update_when_missing() {
        let state = ManagedState::default();
        assert!(state.needs_update("foo", &sample_venv("foo"), "Python 3.12.0",));
    }

    #[test]
    fn no_update_when_unchanged() {
        let mut state = ManagedState::default();
        state.venvs.insert("foo".into(), sample_state("foo"));

        assert!(!state.needs_update("foo", &sample_venv("foo"), "Python 3.12.0",));
    }

    #[test]
    fn needs_update_when_packages_changed() {
        let mut state = ManagedState::default();
        state.venvs.insert("foo".into(), sample_state("foo"));

        let mut changed = sample_venv("foo");
        changed.install.push("flask".into());
        assert!(state.needs_update("foo", &changed, "Python 3.12.0"));
    }

    #[test]
    fn needs_update_when_python_version_changed() {
        let mut state = ManagedState::default();
        state.venvs.insert("foo".into(), sample_state("foo"));

        assert!(state.needs_update("foo", &sample_venv("foo"), "Python 3.13.0",));
    }

    #[test]
    fn orphaned_names_detected() {
        let mut state = ManagedState::default();
        state.venvs.insert("a".into(), sample_state("a"));
        state.venvs.insert("b".into(), sample_state("b"));
        state.venvs.insert("c".into(), sample_state("c"));

        let current: BTreeSet<String> = ["a".into(), "c".into()].into();
        assert_eq!(state.orphaned_names(&current), vec!["b"]);
    }

    #[test]
    fn no_orphans_when_all_present() {
        let mut state = ManagedState::default();
        state.venvs.insert("a".into(), sample_state("a"));

        let current: BTreeSet<String> = ["a".into()].into();
        assert!(state.orphaned_names(&current).is_empty());
    }

    #[test]
    fn roundtrip_serialization() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("managed.json");

        let mut state = ManagedState::default();
        state.venvs.insert(
            "test".into(),
            VenvState {
                config: sample_venv("test"),
                sys_version: "Python 3.12.0".to_string(),
                links: vec![PathBuf::from("/home/user/.local/bin/http")],
            },
        );

        state.save(&path).unwrap();
        let loaded = ManagedState::load(&path).unwrap();
        assert_eq!(state.venvs, loaded.venvs);
    }

    #[test]
    fn save_does_not_leave_temp_file() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("managed.json");

        ManagedState::default().save(&path).unwrap();
        assert!(path.exists());
        assert!(!path.with_extension("json.tmp").exists());
    }

    #[test]
    fn save_overwrites_existing_file_atomically() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("managed.json");
        fs::write(&path, "stale contents").unwrap();

        let mut state = ManagedState::default();
        state.venvs.insert("foo".into(), sample_state("foo"));
        state.save(&path).unwrap();

        let loaded = ManagedState::load(&path).unwrap();
        assert!(loaded.venvs.contains_key("foo"));
    }

    #[test]
    fn load_missing_file_returns_default() {
        let state = ManagedState::load(Path::new("/nonexistent/path")).unwrap();
        assert!(state.venvs.is_empty());
    }

    #[test]
    fn load_corrupted_file_is_an_error() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("managed.json");
        fs::write(&path, "not even json").unwrap();
        assert!(ManagedState::load(&path).is_err());
    }

    #[test]
    fn load_wrong_schema_is_an_error() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("managed.json");
        fs::write(&path, r#"{"something": "else"}"#).unwrap();
        assert!(ManagedState::load(&path).is_err());
    }

    #[test]
    fn load_rejects_tampered_traversal_key() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("managed.json");
        fs::write(
            &path,
            r#"{"venvs":{"../etc":{"config":{"name":"../etc","python":"python3","install":[],"requirements":[],"link":[],"link_module":[],"post_commands":[]},"sys_version":"x","links":[]}}}"#,
        )
        .unwrap();
        let err = ManagedState::load(&path).unwrap_err();
        assert!(format!("{err:#}").contains("../etc"));
    }
}
