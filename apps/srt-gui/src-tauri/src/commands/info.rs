//! Comandi Tauri per informazioni sull'applicazione.

use serde::{Deserialize, Serialize};

/// Informazioni sull'applicazione
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppInfo {
    pub version: String,
    pub name: String,
    pub license: String,
}

/// Ritorna le informazioni sull'applicazione
#[tauri::command]
pub fn get_app_info() -> AppInfo {
    AppInfo {
        version: env!("CARGO_PKG_VERSION").to_string(),
        name: "VESTA".to_string(),
        license: env!("CARGO_PKG_LICENSE").to_string(),
    }
}
