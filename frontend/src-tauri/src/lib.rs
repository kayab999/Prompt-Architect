use tauri::{AppHandle, Manager, State, WindowEvent, Emitter};
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;
use std::sync::Arc;
use tokio::sync::Mutex;
use rand::{distributions::Alphanumeric, Rng};

struct BackendPort(Arc<Mutex<Option<u16>>>);
struct BackendChild(Arc<Mutex<Option<tauri_plugin_shell::process::CommandChild>>>);
struct SystemKey(String);

#[tauri::command]
async fn get_backend_port(port_state: State<'_, BackendPort>) -> Result<u16, String> {
    let mut attempts = 0;
    while attempts < 100 { // 10 seconds max wait
        let lock = port_state.0.lock().await;
        if let Some(port) = *lock {
            return Ok(port);
        }
        drop(lock);
        tokio::time::sleep(std::time::Duration::from_millis(100)).await;
        attempts += 1;
    }
    Err("Backend port not discovered within timeout".into())
}

#[tauri::command]
fn detect_linux_theme() -> String {
    // 1. Try Freedesktop standard DBus portal (Modern GNOME, KDE, XFCE, etc.)
    let dbus_output = std::process::Command::new("dbus-send")
        .args(&[
            "--session",
            "--print-reply=literal",
            "--dest=org.freedesktop.portal.Desktop",
            "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.Settings.Read",
            "string:org.freedesktop.appearance",
            "string:color-scheme"
        ])
        .output();

    if let Ok(output) = dbus_output {
        let stdout = String::from_utf8_lossy(&output.stdout);
        // 1 = Dark, 0 = Light, 2 = Default
        if stdout.contains("uint32 1") {
            return "dark".to_string();
        } else if stdout.contains("uint32 0") || stdout.contains("uint32 2") {
            return "light".to_string();
        }
    }

    // 2. Fallback to older gsettings (mostly GNOME specific)
    let gsettings_output = std::process::Command::new("gsettings")
        .args(&["get", "org.gnome.desktop.interface", "gtk-theme"])
        .output();

    if let Ok(output) = gsettings_output {
        let stdout = String::from_utf8_lossy(&output.stdout);
        if stdout.to_lowercase().contains("dark") {
            return "dark".to_string();
        } else if stdout.to_lowercase().contains("light") {
            return "light".to_string();
        }
    }

    // 3. Absolute fallback for minimal window managers (Linux Lite, bare Openbox, etc)
    if let Some(mut config_path) = dirs::config_dir() {
        config_path.push("gtk-3.0");
        config_path.push("settings.ini");
        if let Ok(content) = std::fs::read_to_string(config_path) {
            if content.contains("gtk-application-prefer-dark-theme=1") {
                return "dark".to_string();
            } else if content.contains("gtk-application-prefer-dark-theme=0") {
                return "light".to_string();
            }
        }
    }

    // Default fallback
    "dark".to_string()
}

async fn shutdown_backend(app: &AppHandle) {
    let port_state = app.state::<BackendPort>();
    let port_lock = port_state.0.lock().await;
    let port = port_lock.unwrap_or(8000);
    drop(port_lock);

    let system_key = app.state::<SystemKey>().0.clone();
    let client = reqwest::Client::new();
    let url = format!("http://127.0.0.1:{}/shutdown", port);
    
    println!("[Tauri] Requesting backend shutdown at {}...", url);
    let _ = client.post(url)
        .header("X-Shutdown-Key", system_key)
        .send()
        .await;
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            let _ = app.get_webview_window("main")
                .expect("no main window")
                .set_focus();
        }))
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_store::Builder::new().build())
        .setup(|app| {
            let app_handle = app.handle().clone();
            
            // Generate secure SYSTEM_KEY from Tauri authority
            let system_key: String = rand::thread_rng()
                .sample_iter(&Alphanumeric)
                .take(32)
                .map(char::from)
                .collect();
            app.manage(SystemKey(system_key.clone()));

            // 1. Spawn Sidecar with injected key
            let (mut rx, child) = app.shell()
                .sidecar("pa-backend")
                .unwrap()
                .env("PA_SYSTEM_KEY", &system_key)
                .spawn()
                .expect("failed to spawn sidecar");

            let child_arc = Arc::new(Mutex::new(Some(child)));
            app.manage(BackendChild(child_arc.clone()));

            // 2. Discover Port asynchronously without blocking UI thread
            let port_state = Arc::new(Mutex::new(None::<u16>));
            app.manage(BackendPort(port_state.clone()));

            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            let text = String::from_utf8_lossy(&line);
                            println!("[PY]: {}", text);
                            if text.starts_with("PA_PORT=") {
                                if let Ok(p) = text.trim_start_matches("PA_PORT=").trim().parse::<u16>() {
                                    println!("[Tauri] Backend discovered on port: {}", p);
                                    let mut lock = port_state.lock().await;
                                    *lock = Some(p);
                                }
                            }
                        }
                        CommandEvent::Stderr(line) => {
                            let text = String::from_utf8_lossy(&line).into_owned();
                            eprintln!("[PY_ERR]: {}", text);
                            let _ = app_handle.emit("backend-error", text);
                        }
                        CommandEvent::Terminated(status) => {
                            println!("[PY]: Terminated with status {:?}", status);
                            let _ = app_handle.emit("backend-error", "Backend process terminated unexpectedly.");
                        }
                        _ => {}
                    }
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { .. } = event {
                let app = window.app_handle().clone();

                tauri::async_runtime::block_on(async move {
                    shutdown_backend(&app).await;

                    let child_state = app.state::<BackendChild>();
                    let mut lock = child_state.0.lock().await;
                    if let Some(child) = lock.take() {
                        let _ = child.kill();
                    }
                });
            }
        })
        .invoke_handler(tauri::generate_handler![get_backend_port, detect_linux_theme])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
