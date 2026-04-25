use std::env;
use std::path::PathBuf;
use std::process::ExitCode;

use clap::Subcommand;

use crate::locator::Locator;

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

pub fn run(locator: &Locator, command: Option<FindCommand>, existing_only: bool) -> ExitCode {
    let (venv_dir, binary) = match command {
        None => {
            println!("{}", locator.root.display());
            return ExitCode::SUCCESS;
        }
        Some(FindCommand::Name { name, binary }) => (locator.for_name(&name), binary),
        Some(FindCommand::Directory { directory, binary }) => {
            let dir = directory
                .unwrap_or_else(|| env::current_dir().unwrap_or_else(|_| PathBuf::from(".")));
            (locator.for_directory(&dir), binary)
        }
    };

    if existing_only && !venv_dir.exists() {
        return ExitCode::FAILURE;
    }

    match binary {
        Some(bin) => {
            println!("{}", venv_dir.join("bin").join(bin).display());
        }
        None => {
            println!("{}", venv_dir.display());
        }
    }

    ExitCode::SUCCESS
}
