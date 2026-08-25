#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command, Stdio};

fn spawn_backend_sidecar() -> Option<Child> {
    let exe = std::env::current_exe().ok()?;
    let dir = exe.parent()?;
    let backend = dir.join("tradeverse-backend.exe");
    if !backend.exists() {
        return None;
    }
    Command::new(backend)
        .env("LOCAL_INSTANCE_MODE", "true")
        .env("AUTO_INIT_DB", "true")
        .env("SERVE_STATIC_UI", "true")
        .env("BACKEND_HOST", "127.0.0.1")
        .env("BACKEND_PORT", "8765")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .ok()
}

fn main() {
    let mut backend_child = spawn_backend_sidecar();

    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("error while running TRADEVERSE");

    if let Some(mut child) = backend_child {
        let _ = child.kill();
    }
}
