//! Actual downstream compilation proves production feature sets hide fixtures.

use std::{
    fs, io,
    path::{Path, PathBuf},
    process::{Command, Output},
    sync::atomic::{AtomicUsize, Ordering},
};

static NEXT_TEMP: AtomicUsize = AtomicUsize::new(0);

struct TempWorkspace(PathBuf);

impl TempWorkspace {
    fn new() -> Self {
        for _ in 0..32 {
            let counter = NEXT_TEMP.fetch_add(1, Ordering::Relaxed);
            let path = std::env::temp_dir().join(format!(
                "rpp-link-feature-visibility-{}-{counter}",
                std::process::id()
            ));
            match fs::create_dir(&path) {
                Ok(()) => return Self(path),
                Err(error) if error.kind() == io::ErrorKind::AlreadyExists => continue,
                Err(error) => panic!("cannot create compile-probe workspace: {error}"),
            }
        }
        panic!("compile-probe workspace names exhausted");
    }
}

impl Drop for TempWorkspace {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn cargo(project: &Path, command: &str, locked: bool) -> Output {
    let executable = std::env::var_os("CARGO").unwrap_or_else(|| "cargo".into());
    let mut child = Command::new(executable);
    child
        .current_dir(project)
        .arg(command)
        .arg("--offline")
        .arg("--quiet");
    if locked {
        child.arg("--locked");
    }
    if command == "check" {
        child.arg("--target-dir").arg(project.join("target"));
    }
    child.output().expect("start offline compile probe")
}

#[test]
fn production_consumers_cannot_import_simulation_fixture() {
    // Mutation default-simulation-leak: changing the module gate back to std
    // makes the default downstream import compile and must fail this assertion.
    let temp = TempWorkspace::new();
    let dependency = Path::new(env!("CARGO_MANIFEST_DIR"))
        .to_string_lossy()
        .replace('\\', "\\\\")
        .replace('"', "\\\"");
    for (name, defaults) in [("default", true), ("bare", false)] {
        let project = temp.0.join(name);
        fs::create_dir_all(project.join("src")).unwrap();
        fs::write(
            project.join("Cargo.toml"),
            format!(
                "[package]\nname = \"rpp-link-{name}-probe\"\nversion = \"0.0.0\"\nedition = \"2021\"\n\n[dependencies]\nrpp-link = {{ path = \"{dependency}\", version = \"=0.1.0\", default-features = {defaults} }}\n\n[workspace]\n"
            ),
        )
        .unwrap();
        fs::write(
            project.join("src/lib.rs"),
            include_str!("fixtures/production_simulation_import.rs"),
        )
        .unwrap();
        let lock = cargo(&project, "generate-lockfile", false);
        assert!(
            lock.status.success(),
            "{name} probe must resolve local locked dependencies: {}",
            String::from_utf8_lossy(&lock.stderr)
        );
        let result = cargo(&project, "check", true);
        let diagnostics = String::from_utf8_lossy(&result.stderr);
        assert_eq!(
            result.status.code(),
            Some(101),
            "{name} production consumer unexpectedly imported a simulation helper"
        );
        assert!(
            diagnostics.contains("E0432") && diagnostics.contains("rpp_link::simulated"),
            "{name} probe must fail on the hidden API, not an unrelated tool error: {diagnostics}"
        );
    }
}
