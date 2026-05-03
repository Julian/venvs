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
            (locator.for_name(&name), binary)
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
