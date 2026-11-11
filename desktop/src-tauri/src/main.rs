#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod private_profile;

use serde_json::{json, Value};
use std::{
    collections::HashMap,
    fs::{File, OpenOptions},
    io::{BufRead, BufReader, Write},
    path::PathBuf,
    process::{Child, ChildStdin, ChildStdout, Command, Stdio},
    sync::{Arc, Mutex},
};
use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem, Submenu},
    tray::TrayIconBuilder,
    webview::PageLoadEvent,
    Emitter, Manager, State,
};

struct Engine {
    child: Child,
    input: ChildStdin,
    output: BufReader<ChildStdout>,
    key: String,
    secrets: HashMap<String, String>,
    refresh_after: HashMap<String, u128>,
    pending_grants: HashMap<String, String>,
    directory: PathBuf,
    vault_service: String,
    _lock: File,
}

impl Engine {
    fn launch(directory: PathBuf, profile: Option<uuid::Uuid>) -> Result<Self, String> {
        let (directory, vault_service) = private_profile::prepare(directory, profile)?;
        std::fs::create_dir_all(&directory).map_err(|_| "storage_unavailable")?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            std::fs::set_permissions(&directory, std::fs::Permissions::from_mode(0o700))
                .map_err(|_| "storage_unavailable")?;
        }
        let lock = OpenOptions::new()
            .create(true)
            .truncate(false)
            .read(true)
            .write(true)
            .open(directory.join("engine.lock"))
            .map_err(|_| "storage_unavailable")?;
        lock.try_lock().map_err(|_| "engine_already_running")?;
        let suffix = if cfg!(windows) { ".exe" } else { "" };
        let beside = std::env::current_exe()
            .map_err(|_| "engine_unavailable")?
            .with_file_name(format!("omr-engine{suffix}"));
        let binary = if beside.exists() {
            beside
        } else {
            PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .join("binaries")
                .join(format!("omr-engine-{}{suffix}", env!("OMR_TARGET")))
        };
        let mut command = Command::new(binary);
        command
            .arg(&directory)
            .env_clear()
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null());
        // Windows loader and frozen Python need these platform directories, never credentials.
        for name in ["SystemRoot", "WINDIR", "TEMP", "TMP", "TMPDIR", "LANG"] {
            if let Some(value) = std::env::var_os(name) {
                command.env(name, value);
            }
        }
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x08000000);
        }
        let mut child = command.spawn().map_err(|_| "engine_unavailable")?;
        let input = child.stdin.take().ok_or("engine_unavailable")?;
        let output = BufReader::new(child.stdout.take().ok_or("engine_unavailable")?);
        let key = format!(
            "{}{}",
            uuid::Uuid::new_v4().simple(),
            uuid::Uuid::new_v4().simple()
        );
        let mut engine = Self {
            child,
            input,
            output,
            key,
            secrets: HashMap::new(),
            refresh_after: HashMap::new(),
            pending_grants: HashMap::new(),
            directory,
            vault_service,
            _lock: lock,
        };
        let snapshot = engine.exchange(json!({"command":"init", "key":engine.key}))?;
        if let Some(connections) = snapshot["config"]["connections"].as_array() {
            for connection in connections {
                if let Some(id) = connection["id"].as_str() {
                    if let Ok(entry) = engine.vault_entry(id) {
                        if let Ok(secret) = entry.get_password() {
                            engine.secrets.insert(id.to_owned(), secret);
                        }
                    }
                }
            }
        }
        if let Ok(entry) = engine.vault_entry(BENCHMARK_SECRET) {
            if let Ok(secret) = entry.get_password() {
                engine.secrets.insert(BENCHMARK_SECRET.to_owned(), secret);
            }
        }
        engine.sync_secrets()?;
        Ok(engine)
    }

    fn exchange(&mut self, request: Value) -> Result<Value, String> {
        serde_json::to_writer(&mut self.input, &request).map_err(|_| "engine_disconnected")?;
        self.input
            .write_all(b"\n")
            .map_err(|_| "engine_disconnected")?;
        self.input.flush().map_err(|_| "engine_disconnected")?;
        let mut line = String::new();
        // The sidecar bounds snapshots to 10k receipts. No logs are on this channel.
        self.output
            .read_line(&mut line)
            .map_err(|_| "engine_disconnected")?;
        let result: Value = serde_json::from_str(&line).map_err(|_| "engine_disconnected")?;
        if let Some(error) = result["error"].as_str() {
            return Err(error.to_owned());
        }
        result
            .get("ok")
            .cloned()
            .ok_or_else(|| "engine_disconnected".into())
    }

    fn sync_secrets(&mut self) -> Result<(), String> {
        self.exchange(json!({"command":"secrets", "values":self.secrets}))?;
        Ok(())
    }

    fn request(&mut self, request: Value) -> Result<Value, String> {
        let command = request["command"].as_str().unwrap_or("").to_owned();
        if command == "credentials" {
            let snapshot = self.exchange(json!({"command":"snapshot"}))?;
            return Ok(
                json!({"endpoint":format!("http://127.0.0.1:{}/v1", snapshot["port"]), "key":self.key}),
            );
        }
        if !allowed(&command) {
            return Err("invalid_command".into());
        }
        if command == "portal" {
            let home = std::env::var_os("HOME").ok_or("portal_unavailable")?;
            let program = [
                PathBuf::from(&home).join(".local/bin/hermes"),
                PathBuf::from("/usr/local/bin/hermes"),
            ]
            .into_iter()
            .find(|path| path.is_file())
            .ok_or("portal_unavailable")?;
            return self.exchange(json!({"command":"portal_connector", "action":request["action"],
                "connection":request["connection"], "program":program, "home":home.to_string_lossy()}));
        }
        if command == "subscription" {
            let id = request["connection"]
                .as_str()
                .ok_or("invalid_command")?
                .to_owned();
            let mut result = self.exchange(request)?;
            if result["status"] == "authenticated" {
                let secret =
                    self.exchange(json!({"command":"subscription_credentials", "connection":id}))?;
                self.store_subscription(&id, secret.as_str().ok_or("subscription_failed")?)?;
                self.invalidate_refresh(&id)?;
                self.sync_secrets()?;
                result =
                    self.exchange(json!({"command":"subscription_commit", "connection":id}))?;
            }
            if matches!(result["status"].as_str(), Some("idle" | "connected")) {
                if let Some(secret) = self.secrets.get(&id) {
                    let value: Value =
                        serde_json::from_str(secret).map_err(|_| "subscription_failed")?;
                    result["status"] = json!(if value["expires"].as_u64().unwrap_or(0) as u128
                        > now_ms()
                    {
                        "connected"
                    } else {
                        "expired"
                    });
                }
            }
            return Ok(result);
        }
        if matches!(
            command.as_str(),
            "snapshot" | "discover" | "test_generation" | "chat_start"
        ) {
            self.refresh_codex()?;
        }
        if command == "export_receipts" {
            let exported = self.exchange(request)?;
            let directory = self.directory.join("exports");
            std::fs::create_dir_all(&directory).map_err(|_| "storage_unavailable")?;
            let path = directory.join(format!("omr-receipts-{}.json", uuid::Uuid::new_v4()));
            std::fs::write(&path, exported.as_str().ok_or("invalid_export")?)
                .map_err(|_| "storage_unavailable")?;
            return Ok(json!({"path":path}));
        }
        let result = self.exchange(request)?;
        if command == "save_config" {
            let connections = result["config"]["connections"]
                .as_array()
                .ok_or("invalid_config")?;
            let current = |id: &String| {
                connections
                    .iter()
                    .any(|c| c["id"] == *id && c["subscription"] == "codex")
            };
            self.pending_grants.retain(|id, _| current(id));
            self.refresh_after.retain(|id, _| current(id));
        }
        if command == "snapshot" || command == "save_config" || command == "test_generation" {
            let mut result = result;
            result["secret_states"] = json!(self.secrets.keys().collect::<Vec<_>>());
            return Ok(result);
        }
        Ok(result)
    }

    fn invalidate_refresh(&mut self, id: &str) -> Result<(), String> {
        self.pending_grants.remove(id);
        self.refresh_after.remove(id);
        self.exchange(json!({"command":"subscription_invalidate", "connection":id}))?;
        Ok(())
    }

    fn vault_entry(&self, id: &str) -> Result<keyring::Entry, String> {
        keyring::Entry::new(&self.vault_service, id).map_err(|_| "vault_unavailable".into())
    }

    fn store_subscription(&mut self, id: &str, secret: &str) -> Result<(), String> {
        let entry = self.vault_entry(id)?;
        entry
            .set_password(secret)
            .map_err(|_| "vault_unavailable")?;
        if entry.get_password().map_err(|_| "vault_unavailable")? != secret {
            return Err("vault_unavailable".into());
        }
        self.secrets.insert(id.to_owned(), secret.to_owned());
        Ok(())
    }

    fn store_refresh(&mut self, id: &str, secret: &str) -> Result<(), String> {
        // Login retries already live in CodexLogin; retain only rotations here.
        self.pending_grants.insert(id.to_owned(), secret.to_owned());
        self.store_subscription(id, secret)?;
        self.sync_secrets()?;
        self.pending_grants.remove(id);
        Ok(())
    }

    fn refresh_pending(&mut self) -> Result<(), String> {
        let pending = self.exchange(json!({"command":"subscription_pending"}))?;
        let requests = pending.as_array().ok_or("subscription_failed")?;
        for request in requests {
            let id = request["connection"]
                .as_str()
                .ok_or("subscription_failed")?;
            let mut generation = request["generation"].clone();
            let result = if let Some(secret) = self.pending_grants.get(id).cloned() {
                self.store_refresh(id, &secret)
            } else if let Some(secret) = self.secrets.get(id).cloned() {
                match self.exchange(
                    json!({"command":"subscription_refresh", "connection":id, "secret":secret}),
                ) {
                    Ok(refreshed) => {
                        generation = refreshed["generation"].clone();
                        if refreshed["status"] == "refreshing" {
                            continue;
                        }
                        if refreshed["status"] == "authenticated" {
                            refreshed["secret"]
                                .as_str()
                                .ok_or_else(|| "subscription_failed".to_owned())
                                .and_then(|secret| self.store_refresh(id, secret))
                        } else {
                            Err("subscription_failed".to_owned())
                        }
                    }
                    Err(_) => Err("subscription_failed".to_owned()),
                }
            } else {
                Err("subscription_expired".to_owned())
            };
            self.exchange(json!({"command":"subscription_refreshed",
                "connection":id, "generation":generation, "error":result.err()}))?;
        }
        Ok(())
    }

    fn refresh_codex(&mut self) -> Result<(), String> {
        let snapshot = self.exchange(json!({"command":"snapshot"}))?;
        let connections = snapshot["config"]["connections"]
            .as_array()
            .ok_or("invalid_config")?;
        for connection in connections.iter().filter(|c| c["subscription"] == "codex") {
            let id = connection["id"].as_str().ok_or("invalid_config")?;
            if let Some(secret) = self.pending_grants.get(id).cloned() {
                let _ = self.store_refresh(id, &secret);
                continue;
            }
            let Some(secret) = self.secrets.get(id).cloned() else {
                continue;
            };
            let Ok(value) = serde_json::from_str::<Value>(&secret) else {
                continue;
            };
            let now = now_ms();
            if value["expires"].as_u64().unwrap_or(0) as u128 > now + 600_000
                || self.refresh_after.get(id).is_some_and(|after| *after > now)
            {
                continue;
            }
            self.refresh_after.insert(id.to_owned(), now + 60_000);
            // Schedule without waiting on another account; refresh_pending commits each grant.
            self.exchange(
                json!({"command":"subscription_refresh", "connection":id, "secret":secret}),
            )?;
        }
        Ok(())
    }
}

fn now_ms() -> u128 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis()
}

impl Drop for Engine {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

fn allowed(command: &str) -> bool {
    matches!(
        command,
        "snapshot"
            | "chat_start"
            | "chat_poll"
            | "chat_cancel"
            | "save_config"
            | "discover"
            | "test_generation"
            | "export_receipts"
            | "native"
            | "managed"
            | "test_decision"
            | "benchmark_refresh"
            | "subscription"
            | "portal"
    )
}

type Shared = Arc<Mutex<Result<Engine, String>>>;

const BENCHMARK_SECRET: &str = "benchmark-artificial-analysis";

#[tauri::command]
async fn engine(state: State<'_, Shared>, request: Value) -> Result<Value, String> {
    let shared = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let mut locked = shared.lock().map_err(|_| "engine_unavailable")?;
        match &mut *locked {
            Ok(engine) => engine.request(request),
            Err(error) => Err(error.clone()),
        }
    })
    .await
    .map_err(|_| "engine_unavailable")?
}

#[tauri::command]
async fn save_secret(
    state: State<'_, Shared>,
    connection: String,
    secret: String,
) -> Result<(), String> {
    let shared = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        if (connection != BENCHMARK_SECRET && uuid::Uuid::parse_str(&connection).is_err())
            || secret.len() > 8192
            || secret.contains(['\r', '\n'])
        {
            return Err("invalid_secret".to_owned());
        }
        let mut locked = shared.lock().map_err(|_| "engine_unavailable")?;
        let engine = locked.as_mut().map_err(|e| e.clone())?;
        let snapshot = engine.exchange(json!({"command":"snapshot"}))?;
        if connection != BENCHMARK_SECRET
            && !snapshot["config"]["connections"]
                .as_array()
                .ok_or("invalid_config")?
                .iter()
                .any(|c| c["id"] == connection)
        {
            return Err("model_unavailable".into());
        }
        let entry = engine.vault_entry(&connection)?;
        let subscription =
            snapshot["config"]["connections"]
                .as_array()
                .is_some_and(|connections| {
                    connections
                        .iter()
                        .any(|c| c["id"] == connection && c.get("subscription").is_some())
                });
        if subscription {
            if !secret.is_empty() {
                return Err("invalid_secret".into());
            }

            let _ = engine.exchange(
                json!({"command":"subscription", "connection":connection, "action":"cancel"}),
            );
        }
        if secret.is_empty() {
            match entry.delete_credential() {
                Ok(()) | Err(keyring::Error::NoEntry) => (),
                Err(_) => return Err("vault_unavailable".into()),
            }
            engine.secrets.remove(&connection);
        } else {
            entry
                .set_password(&secret)
                .map_err(|_| "vault_unavailable")?;
            engine.secrets.insert(connection.clone(), secret);
        }
        engine.invalidate_refresh(&connection)?;
        engine.sync_secrets()
    })
    .await
    .map_err(|_| "engine_unavailable")?
}

#[tauri::command]
async fn quit(app: tauri::AppHandle, state: State<'_, Shared>, force: bool) -> Result<(), String> {
    let shared = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let mut locked = shared.lock().map_err(|_| "engine_unavailable")?;
        if let Ok(engine) = locked.as_mut() {
            engine.exchange(json!({"command":"shutdown", "force":force}))?;
        }
        Ok::<(), String>(())
    })
    .await
    .map_err(|_| "engine_unavailable")??;
    app.exit(0);
    Ok(())
}

fn show(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_focus();
    }
}

#[tauri::command]
async fn open_subscription_login(
    state: State<'_, Shared>,
    connection: String,
) -> Result<(), String> {
    let shared = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let mut locked = shared.lock().map_err(|_| "engine_unavailable")?;
        let engine = locked.as_mut().map_err(|e| e.clone())?;
        let snapshot = engine.exchange(json!({"command":"snapshot"}))?;
        let c = snapshot["config"]["connections"]
            .as_array()
            .ok_or("invalid_config")?
            .iter()
            .find(|c| c["id"] == connection)
            .ok_or("model_unavailable")?;
        let url = if c["subscription"] == "codex" {
            "https://auth.openai.com/codex/device".to_owned()
        } else if c["subscription"] == "nous" {
            let status = engine
                .request(json!({"command":"portal", "connection":connection, "action":"status"}))?;
            let url = status["auth"]["url"].as_str().ok_or("portal_unavailable")?;
            if !url.starts_with("https://portal.nousresearch.com/")
                || url.len() > 2048
                || url.chars().any(char::is_control)
            {
                return Err("portal_unavailable".to_owned());
            }
            url.to_owned()
        } else {
            return Err("invalid_command".to_owned());
        };
        open_auth_url(&url)
    })
    .await
    .map_err(|_| "engine_unavailable")?
}

fn open_auth_url(url: &str) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    let mut command = Command::new("/usr/bin/open");
    #[cfg(target_os = "linux")]
    let mut command = Command::new("xdg-open");
    #[cfg(target_os = "windows")]
    let mut command = {
        let mut c = Command::new("rundll32.exe");
        c.arg("url.dll,FileProtocolHandler");
        c
    };
    command
        .arg(url)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|_| "browser_unavailable")?;
    Ok(())
}

fn main() {
    let profile = private_profile::select(std::env::var_os("OMR_DESKTOP_PROFILE").as_deref())
        .unwrap_or_else(|error| {
            eprintln!("{error}");
            std::process::exit(1);
        });
    if profile.is_some() {
        #[cfg(target_os = "macos")]
        let supported = Command::new("/usr/bin/sw_vers")
            .arg("-productVersion")
            .output()
            .ok()
            .filter(|output| output.status.success())
            .and_then(|output| String::from_utf8(output.stdout).ok())
            .and_then(|version| version.trim().split('.').next()?.parse::<u32>().ok())
            .is_some_and(|major| major >= 14);
        #[cfg(not(target_os = "macos"))]
        let supported = false;
        if !supported {
            eprintln!("profile_unavailable: private profiles require macOS 14 or later");
            std::process::exit(1);
        }
    }
    let mut context = tauri::generate_context!();
    let private_windows =
        private_profile::take_windows(&mut context.config_mut().app.windows, profile);
    let mut builder = tauri::Builder::default();
    if profile.is_none() {
        builder = builder.plugin(tauri_plugin_autostart::Builder::new().build());
    }
    builder
        .invoke_handler(tauri::generate_handler![
            engine,
            save_secret,
            quit,
            open_subscription_login
        ])
        .setup(move |app| {
            let directory = app.path().app_data_dir()?;
            let mut runtime = Engine::launch(directory, profile);
            let status_text = match runtime.as_mut() {
                Ok(engine) => match engine.exchange(json!({"command":"snapshot"})) {
                    Ok(snapshot) => format!("Gateway local · port {}", snapshot["port"]),
                    Err(_) => "Moteur indisponible".to_owned(),
                },
                Err(_) => "Moteur indisponible".to_owned(),
            };
            let runtime = Arc::new(Mutex::new(runtime));
            let refresh_owner = Arc::downgrade(&runtime);
            app.manage(runtime);
            if let Some(id) = profile {
                for config in private_windows {
                    tauri::WebviewWindowBuilder::from_config(app, &config)?
                        .data_store_identifier(*id.as_bytes())
                        .build()?;
                }
            }
            // The native vault remains available when the WebView is hidden or suspended.
            std::thread::spawn(move || loop {
                std::thread::sleep(std::time::Duration::from_secs(1));
                let Some(runtime) = refresh_owner.upgrade() else {
                    break;
                };
                let Ok(mut state) = runtime.try_lock() else {
                    continue;
                };
                if let Ok(engine) = state.as_mut() {
                    let _ = engine.refresh_pending();
                }
            });
            let status = MenuItem::with_id(app, "status", status_text, false, None::<&str>)?;
            let open = MenuItem::with_id(app, "open", "Ouvrir OMR Desktop", true, None::<&str>)?;
            let providers =
                MenuItem::with_id(app, "providers", "Fournisseurs", true, None::<&str>)?;
            let usage = MenuItem::with_id(app, "usage", "Consommation", true, None::<&str>)?;
            let quit = MenuItem::with_id(
                app,
                "quit",
                "Quitter OMR Desktop…",
                true,
                Some("CmdOrCtrl+Q"),
            )?;
            let menu = Menu::with_items(app, &[&status, &open, &providers, &usage, &quit])?;
            let app_menu = Submenu::with_items(
                app,
                "OMR Desktop",
                true,
                &[&status, &open, &providers, &usage, &quit],
            )?;
            let edit_menu = Submenu::with_items(
                app,
                "Édition",
                true,
                &[
                    &PredefinedMenuItem::undo(app, None)?,
                    &PredefinedMenuItem::redo(app, None)?,
                    &PredefinedMenuItem::cut(app, None)?,
                    &PredefinedMenuItem::copy(app, None)?,
                    &PredefinedMenuItem::paste(app, None)?,
                    &PredefinedMenuItem::select_all(app, None)?,
                ],
            )?;
            app.set_menu(Menu::with_items(app, &[&app_menu, &edit_menu])?)?;
            app.on_menu_event(|app, event| match event.id().as_ref() {
                "open" => show(app),
                "providers" | "usage" => {
                    show(app);
                    let _ = app.emit(
                        "navigate",
                        if event.id().as_ref() == "providers" {
                            "Fournisseurs"
                        } else {
                            "Consommation"
                        },
                    );
                }
                "quit" => {
                    show(app);
                    let _ = app.emit("quit-requested", ());
                }
                _ => (),
            });
            let icon_bytes: &[u8] = if cfg!(target_os = "macos") {
                include_bytes!("../icons/tray-template.png")
            } else {
                include_bytes!("../icons/tray.png")
            };
            let icon = tauri::image::Image::from_bytes(icon_bytes)?;
            let tray = TrayIconBuilder::new()
                .icon(icon)
                .icon_as_template(cfg!(target_os = "macos"))
                .menu(&menu)
                .tooltip("OMR Desktop — routeur local")
                .build(app)
                .is_ok();
            let handle = app.handle().clone();
            if let Some(window) = app.get_webview_window("main") {
                window.on_window_event(move |event| {
                    if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                        api.prevent_close();
                        if cfg!(target_os = "linux") {
                            if let Some(w) = handle.get_webview_window("main") {
                                let _ = w.minimize();
                            }
                        } else if tray {
                            if let Some(w) = handle.get_webview_window("main") {
                                let _ = w.hide();
                            }
                        } else {
                            let _ = handle.emit("quit-requested", ());
                        }
                    }
                });
            }
            Ok(())
        })
        // Adapted from tauri-ui's pinned flash-prevention battery.
        .on_page_load(|webview, payload| {
            if webview.label() == "main" && matches!(payload.event(), PageLoadEvent::Finished) {
                let _ = webview.window().show();
            }
        })
        .build(context)
        .expect("Unable to initialize OMR Desktop")
        .run(|app, event| {
            if let tauri::RunEvent::ExitRequested {
                api, code: None, ..
            } = event
            {
                api.prevent_exit();
                show(app);
                let _ = app.emit("quit-requested", ());
            }
        });
}

#[cfg(test)]
mod tests {
    use super::*;
    use keyring::credential::CredentialApi;
    use std::sync::atomic::{AtomicBool, Ordering};

    static VAULT_TEST_LOCK: Mutex<()> = Mutex::new(());
    type MockItems = Arc<Mutex<HashMap<(String, String), Arc<keyring::mock::MockCredential>>>>;
    #[derive(Clone, Default)]
    struct FailingMockVault {
        fail_next: Arc<AtomicBool>,
        items: MockItems,
        services: Arc<Mutex<Vec<String>>>,
    }
    struct SharedMockCredential(Arc<keyring::mock::MockCredential>);
    impl CredentialApi for SharedMockCredential {
        fn set_secret(&self, secret: &[u8]) -> keyring::Result<()> {
            self.0.set_secret(secret)
        }
        fn get_secret(&self) -> keyring::Result<Vec<u8>> {
            self.0.get_secret()
        }
        fn delete_credential(&self) -> keyring::Result<()> {
            self.0.delete_credential()
        }
        fn as_any(&self) -> &dyn std::any::Any {
            self
        }
    }
    impl keyring::credential::CredentialBuilderApi for FailingMockVault {
        fn build(
            &self,
            _: Option<&str>,
            service: &str,
            account: &str,
        ) -> keyring::Result<Box<keyring::credential::Credential>> {
            self.services.lock().unwrap().push(service.into());
            let credential = self
                .items
                .lock()
                .unwrap()
                .entry((service.into(), account.into()))
                .or_insert_with(|| Arc::new(keyring::mock::MockCredential::default()))
                .clone();
            if self.fail_next.swap(false, Ordering::SeqCst) {
                credential.set_error(keyring::Error::NoEntry);
            }
            Ok(Box::new(SharedMockCredential(credential)))
        }
        fn as_any(&self) -> &dyn std::any::Any {
            self
        }
    }

    #[test]
    fn reconnect_fences_old_refresh_before_native_vault_commit() {
        // Real owner methods + private JSONL + Python queue; no OS vault or provider access.
        let _guard = VAULT_TEST_LOCK.lock().unwrap();
        let vault = FailingMockVault::default();
        let fail_next = vault.fail_next.clone();
        keyring::set_default_credential_builder(Box::new(vault));
        let old_secret = format!(
            r#"{{"access": "old-grant", "expires": {}, "refresh": "fixture-refresh"}}"#,
            now_ms() + 300_000
        );
        for (access, action) in [
            ("new-grant", "reconnect"),
            ("old-grant", "reconnect"),
            ("new-grant", "retry"),
            ("new-grant", "cancel"),
        ] {
            let login_secret = if access == "old-grant" {
                old_secret.clone()
            } else {
                format!(
                    r#"{{"access": "{access}", "expires": {}, "refresh": "fixture-new-refresh"}}"#,
                    now_ms() + 300_000
                )
            };
            let directory =
                std::env::temp_dir().join(format!("omr-refresh-{}", uuid::Uuid::new_v4()));
            std::fs::create_dir(&directory).unwrap();
            let id = uuid::Uuid::new_v4().to_string();
            let script = r#"
import json,sys,threading,time
import desktop_subscriptions as s
q=s.NativeRefresh(threading.RLock())
login=s.CodexLogin()
login.connection=sys.argv[1]; login.value=json.loads(sys.argv[2]); login.status='authenticated'
release=threading.Event()
old=None
def refresh(secret):
    if not release.wait(5): raise ValueError('fixture_timeout')
    grant=json.loads(secret); grant['access']='rotated-'+grant['access']
    return json.dumps(grant)
s.refresh=refresh
for line in sys.stdin:
    r=json.loads(line); c=r['command']; result=True
    if c=='snapshot': result={'config':{'connections':[{'id':sys.argv[1],'subscription':'codex'}]}}
    elif c=='subscription': result=login.cancel() if r.get('action')=='cancel' else login.snapshot()
    elif c=='subscription_credentials': result=login.credentials(r['connection'])
    elif c=='subscription_commit': result=login.commit(r['connection'])
    elif c=='subscription_invalidate': q.invalidate(r['connection'])
    elif c=='subscription_pending': result=q.pending()
    elif c=='subscription_refresh':
        result=q.poll(r['connection'],r['secret'])
        if old is None: old=q.requests[r['connection']]
    elif c=='subscription_refreshed': q.finish(r['connection'],r['generation'],r.get('error'))
    elif c=='fixture_release':
        release.set(); deadline=time.monotonic()+2
        while old['result'] is None and time.monotonic()<deadline: time.sleep(.005)
        assert old['result'] is not None
    elif c!='secrets': raise AssertionError(c)
    print(json.dumps({'ok':result}),flush=True)
"#;
            let mut child = Command::new(
                std::env::var_os("OMR_TEST_PYTHON").unwrap_or_else(|| "python3".into()),
            )
            .args(["-u", "-c", script, &id, &login_secret])
            .current_dir(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."))
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .spawn()
            .unwrap();
            let mut engine = Engine {
                input: child.stdin.take().unwrap(),
                output: BufReader::new(child.stdout.take().unwrap()),
                child,
                key: "fixture".into(),
                secrets: HashMap::from([(id.clone(), old_secret.clone())]),
                refresh_after: HashMap::new(),
                pending_grants: HashMap::new(),
                _lock: File::create(directory.join("lock")).unwrap(),
                directory: directory.clone(),
                vault_service: private_profile::DEFAULT_SERVICE.into(),
            };
            engine
                .exchange(
                    json!({"command":"subscription_refresh", "connection":id, "secret":old_secret}),
                )
                .unwrap();
            if action == "reconnect" {
                engine.pending_grants.insert(id.clone(), old_secret.clone());
            } else {
                fail_next.store(true, Ordering::SeqCst);
                assert_eq!(
                    engine.request(
                        json!({"command":"subscription", "connection":id, "action":"status"})
                    ),
                    Err("vault_unavailable".into())
                );
                if action == "cancel" {
                    engine
                        .request(
                            json!({"command":"subscription", "connection":id, "action":"cancel"}),
                        )
                        .unwrap();
                }
                engine.request(json!({"command":"snapshot"})).unwrap();
                assert_eq!(
                    engine.secrets.get(&id).unwrap(),
                    &old_secret,
                    "snapshot must not commit an uncommitted/cancelled login"
                );
                if action == "cancel" {
                    engine
                        .exchange(json!({"command":"fixture_release"}))
                        .unwrap();
                    engine.refresh_pending().unwrap();
                    assert_ne!(engine.secrets.get(&id).unwrap(), &login_secret);
                    drop(engine);
                    std::fs::remove_dir_all(directory).unwrap();
                    continue;
                }
            }
            engine
                .request(json!({"command":"subscription", "connection":id, "action":"status"}))
                .unwrap();
            assert!(engine
                .exchange(json!({"command":"subscription_pending"}))
                .unwrap()
                .as_array()
                .unwrap()
                .is_empty());
            engine
                .exchange(json!({"command":"fixture_release"}))
                .unwrap();
            engine.refresh_pending().unwrap();
            assert_eq!(engine.secrets.get(&id).unwrap(), &login_secret);
            assert!(engine.pending_grants.is_empty());
            // After an accepted login rotates, a later status poll must not restore its old grant.
            engine.exchange(json!({"command":"subscription_refresh", "connection":id, "secret":login_secret})).unwrap();
            engine
                .exchange(json!({"command":"fixture_release"}))
                .unwrap();
            for _ in 0..100 {
                engine.refresh_pending().unwrap();
                if engine.secrets.get(&id) != Some(&login_secret) {
                    break;
                }
                std::thread::sleep(std::time::Duration::from_millis(5));
            }
            let rotated = engine.secrets.get(&id).unwrap().clone();
            assert_ne!(rotated, login_secret);
            engine
                .request(json!({"command":"subscription", "connection":id, "action":"status"}))
                .unwrap();
            assert_eq!(engine.secrets.get(&id).unwrap(), &rotated);
            drop(engine);
            std::fs::remove_dir_all(directory).unwrap();
        }
    }

    #[cfg(unix)]
    #[test]
    fn private_profiles_scope_real_owner_storage_reload_and_deletion() {
        // Real packaged engine and owner persistence; only Keychain is an in-memory fixture.
        let _guard = VAULT_TEST_LOCK.lock().unwrap();
        let vault = FailingMockVault::default();
        let id = uuid::Uuid::new_v4().to_string();
        for account in [id.as_str(), BENCHMARK_SECRET] {
            let entry = Arc::new(keyring::mock::MockCredential::default());
            entry.set_password("normal-profile-fixture").unwrap();
            vault.items.lock().unwrap().insert(
                (private_profile::DEFAULT_SERVICE.into(), account.into()),
                entry,
            );
        }
        keyring::set_default_credential_builder(Box::new(vault.clone()));
        let home = std::env::var_os("HOME");
        let base = std::env::temp_dir().join(format!("omr-private-owner-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir(&base).unwrap();
        let base = base.canonicalize().unwrap();
        std::fs::write(base.join("providers.json"), b"normal profile sentinel").unwrap();
        let first = uuid::Uuid::new_v4();
        let second = uuid::Uuid::new_v4();
        let mut a = Engine::launch(base.clone(), Some(first)).unwrap();
        let mut b = Engine::launch(base.clone(), Some(second)).unwrap();
        assert!(!a.secrets.contains_key(BENCHMARK_SECRET));
        assert!(!b.secrets.contains_key(BENCHMARK_SECRET));
        assert!(matches!(
            a.vault_entry(&id).unwrap().get_password(),
            Err(keyring::Error::NoEntry)
        ));
        assert!(
            matches!(Engine::launch(base.clone(), Some(first)), Err(error) if error == "engine_already_running")
        );
        let grant = |access: &str| {
            json!({"access":access,"refresh":"fixture-refresh","expires":now_ms()+300_000})
                .to_string()
        };
        let grant_a = grant("fixture-a");
        let grant_b = grant("fixture-b");
        a.store_subscription(&id, &grant_a).unwrap();
        b.store_subscription(&id, &grant_b).unwrap();
        a.vault_entry(BENCHMARK_SECRET)
            .unwrap()
            .set_password("benchmark-a")
            .unwrap();
        b.vault_entry(BENCHMARK_SECRET)
            .unwrap()
            .set_password("benchmark-b")
            .unwrap();
        drop(a);
        drop(b);
        let mut a = Engine::launch(base.clone(), Some(first)).unwrap();
        let b = Engine::launch(base.clone(), Some(second)).unwrap();
        assert_eq!(a.secrets.get(BENCHMARK_SECRET).unwrap(), "benchmark-a");
        assert_eq!(b.secrets.get(BENCHMARK_SECRET).unwrap(), "benchmark-b");
        assert_eq!(a.vault_entry(&id).unwrap().get_password().unwrap(), grant_a);
        assert_eq!(b.vault_entry(&id).unwrap().get_password().unwrap(), grant_b);
        vault.fail_next.store(true, Ordering::SeqCst);
        assert_eq!(
            a.store_subscription(&id, &grant("rejected")),
            Err("vault_unavailable".into())
        );
        a.vault_entry(&id).unwrap().delete_credential().unwrap();
        assert!(matches!(
            a.vault_entry(&id).unwrap().get_password(),
            Err(keyring::Error::NoEntry)
        ));
        assert_eq!(b.vault_entry(&id).unwrap().get_password().unwrap(), grant_b);
        assert!(vault
            .services
            .lock()
            .unwrap()
            .iter()
            .all(|service| service != private_profile::DEFAULT_SERVICE));
        for account in [id.as_str(), BENCHMARK_SECRET] {
            assert_eq!(
                vault
                    .items
                    .lock()
                    .unwrap()
                    .get(&(private_profile::DEFAULT_SERVICE.into(), account.into()))
                    .unwrap()
                    .get_password()
                    .unwrap(),
                "normal-profile-fixture"
            );
        }
        assert_eq!(std::env::var_os("HOME"), home);
        assert_eq!(
            std::fs::read(base.join("providers.json")).unwrap(),
            b"normal profile sentinel"
        );
        drop(a);
        drop(b);
        std::fs::remove_dir_all(base).unwrap();
    }

    #[test]
    fn webview_cannot_inject_keys_commands_or_shutdown() {
        for command in ["init", "secrets", "shutdown", "shell", "read_file", ""] {
            assert!(!allowed(command));
        }
        assert!(allowed("save_config"));
        assert!(allowed("test_generation"));
        for command in ["chat_start", "chat_poll", "chat_cancel"] {
            assert!(allowed(command));
        }
        assert!(!allowed("chat_shell"));
        assert!(allowed("subscription"));
        for command in [
            "subscription_credentials",
            "subscription_refresh",
            "subscription_commit",
            "subscription_pending",
            "subscription_refreshed",
            "subscription_invalidate",
            "portal_connector",
        ] {
            assert!(!allowed(command));
        }
    }
}
