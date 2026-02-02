//! Gestione dello stato globale dell'applicazione.

use std::sync::Mutex;
use srt_sync_lib::SyncEngine;

/// Stato per la sincronizzazione sottotitoli
pub struct SyncState {
    pub engine: Option<SyncEngine>,
}

impl Default for SyncState {
    fn default() -> Self {
        Self { engine: None }
    }
}

/// Wrapper thread-safe per lo stato di sincronizzazione
pub type AppSyncState = Mutex<SyncState>;

/// Stato per la traduzione (configurazione)
#[derive(Default)]
pub struct TranslateState {
    pub api_key: Option<String>,
    pub api_type: Option<String>,
    pub is_translating: bool,
}

/// Wrapper thread-safe per lo stato di traduzione
pub type AppTranslateState = Mutex<TranslateState>;
