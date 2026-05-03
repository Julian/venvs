mod config;
mod converge;
mod find;
mod locator;
mod state;

use std::path::PathBuf;
use std::process::ExitCode;

use clap::{Parser, Subcommand};

use crate::converge::Strategy;

#[derive(Parser)]
#[command(name = "venvs", about = "Centralized virtual environments.", version)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Converge the configured set of tracked virtualenvs.
    Converge {
        /// Fail if any virtualenv cannot be converged.
        #[arg(long)]
        fail_fast: bool,

        /// Print the actions that would be taken without performing them.
        #[arg(long, conflicts_with = "fail_fast")]
        dry_run: bool,

        /// The directory to link scripts into.
        #[arg(long, default_value = "~/.local/bin")]
        link_dir: String,

        /// Specify a different root directory for virtualenvs.
        #[arg(long)]
        root: Option<PathBuf>,

        /// Only converge these specific virtualenvs.
        names: Vec<String>,
    },

    /// Find a virtualenv in the store.
    Find {
        #[command(subcommand)]
        command: Option<find::FindCommand>,

        /// Specify a different root directory for virtualenvs.
        #[arg(long)]
        root: Option<PathBuf>,

        /// Only consider existing virtualenvs.
        #[arg(short = 'E', long)]
        existing_only: bool,
    },
}

fn main() -> ExitCode {
    let cli = Cli::parse();

    let result = match cli.command {
        Commands::Converge {
            fail_fast,
            dry_run,
            link_dir,
            root,
            names,
        } => {
            let link_dir: PathBuf = shellexpand::tilde(&link_dir).to_string().into();
            match locator::Locator::new(root) {
                Ok(locator) => {
                    if dry_run {
                        converge::DryRun.run(&locator, &link_dir, &names)
                    } else {
                        converge::Apply { fail_fast }.run(&locator, &link_dir, &names)
                    }
                }
                Err(e) => Err(e),
            }
        }
        Commands::Find {
            command,
            root,
            existing_only,
        } => match locator::Locator::new(root) {
            Ok(locator) => find::run(&locator, command, existing_only),
            Err(e) => Err(e),
        },
    };

    match result {
        Ok(code) => code,
        Err(e) => {
            eprintln!("error: {e:#}");
            ExitCode::FAILURE
        }
    }
}
