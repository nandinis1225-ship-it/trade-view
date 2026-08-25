#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::thread;
use std::time::Duration;

use tauri::Manager;

const BACKEND_HOST: &str = "127.0.0.1";
const BACKEND_PORT: u16 = 8765;
const HEALTH_PATH: &str = "/api/v1/health";

fn app_dir() -> Option<PathBuf> {
    std::env::current_exe().ok()?.parent().map(|p| p.to_path_buf())
}

fn backend_binary(dir: &PathBuf) -> PathBuf {
    #[cfg(target_os = "windows")]
    {
        dir.join("tradeverse-backend.exe")
    }
    #[cfg(not(target_os = "windows"))]
    {
        dir.join("tradeverse-backend")
    }
}

fn spawn_backend_sidecar(dir: &PathBuf) -> Option<Child> {
    let backend = backend_binary(dir);
    if !backend.exists() {
        eprintln!("TRADEVERSE: backend not found at {}", backend.display());
        return None;
    }
    Command::new(&backend)
        .current_dir(dir)
        .env("LOCAL_INSTANCE_MODE", "true")
        .env("PARTICIPANT_EVENT_MODE", "true")
        .env("AUTO_INIT_DB", "true")
        .env("SERVE_STATIC_UI", "true")
        .env("HIDE_ADMIN_UI", "true")
        .env("DEVELOPER_MODE", "false")
        .env("ENVIRONMENT", "production")
        .env("DEBUG", "false")
        .env("BACKEND_HOST", BACKEND_HOST)
        .env("BACKEND_PORT", BACKEND_PORT.to_string())
        .env("UI_STATIC_DIR", dir.join("ui").to_string_lossy().to_string())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .ok()
}

fn wait_for_backend() -> bool {
    let url = format!("http://{BACKEND_HOST}:{BACKEND_PORT}{HEALTH_PATH}");
    for _ in 0..120 {
        if ureq::get(&url).call().is_ok() {
            return true;
        }
        thread::sleep(Duration::from_millis(500));
    }
    false
}

fn main() {
    let dir = match app_dir() {
        Some(d) => d,
        None => {
            eprintln!("TRADEVERSE: could not resolve application directory");
            std::process::exit(1);
        }
    };

    let mut backend_child = spawn_backend_sidecar(&dir);
    if backend_child.is_none() {
        eprintln!("TRADEVERSE: failed to start local backend");
        std::process::exit(1);
    }

    if !wait_for_backend() {
        eprintln!(
            "TRADEVERSE: backend did not become healthy at http://{}:{}{}",
            BACKEND_HOST, BACKEND_PORT, HEALTH_PATH
        );
        if let Some(mut child) = backend_child.take() {
            let _ = child.kill();
        }
        std::process::exit(1);
    }

    let terminal_url = format!("http://{BACKEND_HOST}:{BACKEND_PORT}/terminal");

    tauri::Builder::default()
        .setup(move |app| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.eval(&format!("window.location.replace('{terminal_url}');"));
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running TRADEVERSE");

    if let Some(mut child) = backend_child {
        let _ = child.kill();
    }
}
