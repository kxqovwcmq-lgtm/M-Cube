#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use tauri::{Manager, RunEvent};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

struct BackendProcessState(Mutex<Option<CommandChild>>);

fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcessState(Mutex::new(None)))
        .setup(|app| {
            if cfg!(debug_assertions) {
                // In dev mode, backend is expected to run separately (uvicorn).
                return Ok(());
            }

            let app_handle = app.handle().clone();

            let app_data_dir = app_handle
                .path()
                .app_data_dir()
                .map_err(|e| format!("Failed to resolve app data directory: {e}"))?;
            std::fs::create_dir_all(&app_data_dir)
                .map_err(|e| format!("Failed to create app data directory: {e}"))?;
            let upload_root = app_data_dir.join("runtime").join("uploads");
            std::fs::create_dir_all(&upload_root)
                .map_err(|e| format!("Failed to create upload root directory: {e}"))?;

            let cmd = match app_handle.shell().sidecar("mcube-backend") {
                Ok(c) => c
                    .env("UPLOAD_ROOT_DIR", upload_root.to_string_lossy().to_string())
                    .env("MCUBE_BACKEND_HOST", "127.0.0.1")
                    .env("MCUBE_BACKEND_PORT", "8000"),
                Err(e) => {
                    eprintln!("Failed to prepare backend sidecar command: {e}");
                    return Ok(());
                }
            };

            let (_rx, child) = match cmd.spawn() {
                Ok(v) => v,
                Err(e) => {
                    eprintln!("Failed to spawn backend sidecar: {e}");
                    return Ok(());
                }
            };

            let state = app_handle.state::<BackendProcessState>();
            let mut guard = state
                .0
                .lock()
                .map_err(|_| String::from("Failed to lock backend process state"))?;
            *guard = Some(child);
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|app_handle, event| {
        if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
            let state = app_handle.state::<BackendProcessState>();
            let child_to_kill = match state.0.lock() {
                Ok(mut guard) => guard.take(),
                Err(_) => None,
            };
            if let Some(child) = child_to_kill {
                let _ = child.kill();
            }
        }
    });
}
