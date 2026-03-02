// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use std::path::Path;
use std::fs;
use std::io::{Read, Seek, SeekFrom};

mod commands;
mod state;

use axum::{
    extract::{Query, Request},
    response::IntoResponse,
    routing::get,
    Router,
};
use tower_http::{
    cors::{Any, CorsLayer},
    services::ServeFile,
};
use tower::ServiceExt;

#[derive(serde::Deserialize)]
struct MediaParams {
    path: String,
}

struct MediaServerPort(u16);

#[tauri::command]
fn get_media_server_port(port: tauri::State<MediaServerPort>) -> u16 {
    port.0
}

async fn media_handler(Query(params): Query<MediaParams>, req: Request) -> Result<impl IntoResponse, axum::http::StatusCode> {
    ServeFile::new(&params.path)
        .oneshot(req)
        .await
        .map_err(|_| axum::http::StatusCode::INTERNAL_SERVER_ERROR)
}

use commands::info::*;
use commands::sync::*;
use commands::translate::*;
use commands::flashcards::*;
use commands::transcribe::*;
use state::{AppSyncState, AppTranslateState, AppFlashcardState, AppTranscribeState, SyncState, TranslateState, FlashcardState, TranscribeState};

/// Determina il MIME type in base all'estensione
fn mime_from_ext(path: &str) -> &'static str {
    match Path::new(path)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_lowercase()
        .as_str()
    {
        "mp4" | "m4v" => "video/mp4",
        "webm" => "video/webm",
        "mkv" => "video/x-matroska",
        "avi" => "video/x-msvideo",
        "mov" => "video/quicktime",
        "ogv" => "video/ogg",
        "mp3" => "audio/mpeg",
        "wav" | "wave" => "audio/wav",
        "ogg" | "oga" => "audio/ogg",
        "flac" => "audio/flac",
        "m4a" => "audio/mp4",
        "aac" => "audio/aac",
        "wma" => "audio/x-ms-wma",
        _ => "application/octet-stream",
    }
}

fn main() {
    // Fix blurry rendering on Linux (WebKitGTK DMABUF renderer issue)
    #[cfg(target_os = "linux")]
    {
        std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "1");
    }

    let listener = std::net::TcpListener::bind("127.0.0.1:0").expect("Failed to bind random port");
    listener.set_nonblocking(true).unwrap();
    let port = listener.local_addr().unwrap().port();
    
    tauri::async_runtime::spawn(async move {
        let cors = CorsLayer::new()
            .allow_origin(Any)
            .allow_methods(Any)
            .allow_headers(Any);
            
        let app = Router::new()
            .route("/media", get(media_handler))
            .layer(cors);
            
        let tokio_listener = tokio::net::TcpListener::from_std(listener).unwrap();
        axum::serve(tokio_listener, app).await.unwrap();
    });

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_http::init())
        // Protocollo custom per lo streaming video con supporto Range requests
        .register_asynchronous_uri_scheme_protocol("stream", |_ctx, request, responder| {
            std::thread::spawn(move || {
                let uri = request.uri().to_string();
                // URI formato: stream://localhost/<encoded_path>
                let path = uri
                    .strip_prefix("stream://localhost/")
                    .or_else(|| uri.strip_prefix("stream://localhost"))
                    .unwrap_or("");
                let path = urlencoding::decode(path).unwrap_or_else(|_| path.into());
                let path = path.to_string();

                eprintln!("[stream] Request URI: {}", uri);
                eprintln!("[stream] Decoded path: '{}'", path);

                // Verifica che il file esista
                let metadata = match fs::metadata(&path) {
                    Ok(m) => m,
                    Err(e) => {
                        eprintln!("[stream] File not found or inaccessible: '{}' - Error: {}", path, e);
                        let resp = tauri::http::Response::builder()
                            .status(404)
                            .header("Content-Type", "text/plain")
                            .body(format!("File not found: {} - {}", path, e).into_bytes())
                            .unwrap();
                        responder.respond(resp);
                        return;
                    }
                };

                let file_size = metadata.len();
                let mime = mime_from_ext(&path);
                eprintln!("[stream] File: '{}', size: {} bytes, mime: {}", path, file_size, mime);

                // Parse Range header
                let range_header = request.headers().get("range").and_then(|v| v.to_str().ok());

                if let Some(range_str) = range_header {
                    eprintln!("[stream] Range request: {}", range_str);
                    // Parse "bytes=START-END" or "bytes=START-"
                    let range_str = range_str.trim_start_matches("bytes=");
                    let parts: Vec<&str> = range_str.split('-').collect();
                    let start: u64 = parts.first().and_then(|s| s.parse().ok()).unwrap_or(0);
                    let end: u64 = parts
                        .get(1)
                        .and_then(|s| if s.is_empty() { None } else { s.parse().ok() })
                        .unwrap_or(file_size - 1)
                        .min(file_size - 1);

                    let chunk_size = end - start + 1;

                    // Leggi il chunk richiesto
                    let mut file = match fs::File::open(&path) {
                        Ok(f) => f,
                        Err(_) => {
                            let resp = tauri::http::Response::builder()
                                .status(500)
                                .body(b"Failed to open file".to_vec())
                                .unwrap();
                            responder.respond(resp);
                            return;
                        }
                    };

                    if file.seek(SeekFrom::Start(start)).is_err() {
                        let resp = tauri::http::Response::builder()
                            .status(500)
                            .body(b"Seek failed".to_vec())
                            .unwrap();
                        responder.respond(resp);
                        return;
                    }

                    // Limita chunk a 4MB per evitare uso eccessivo di memoria
                    let max_chunk = 4 * 1024 * 1024u64;
                    let read_size = chunk_size.min(max_chunk) as usize;
                    let mut buf = vec![0u8; read_size];
                    let bytes_read = match file.read(&mut buf) {
                        Ok(n) => n,
                        Err(_) => {
                            let resp = tauri::http::Response::builder()
                                .status(500)
                                .body(b"Read failed".to_vec())
                                .unwrap();
                            responder.respond(resp);
                            return;
                        }
                    };
                    buf.truncate(bytes_read);

                    let actual_end = start + bytes_read as u64 - 1;

                    eprintln!("[stream] Range response: bytes {}-{}/{}, chunk={} bytes", start, actual_end, file_size, bytes_read);

                    let resp = tauri::http::Response::builder()
                        .status(206)
                        .header("Content-Type", mime)
                        .header("Accept-Ranges", "bytes")
                        .header("Content-Range", format!("bytes {}-{}/{}", start, actual_end, file_size))
                        .header("Content-Length", bytes_read.to_string())
                        .body(buf)
                        .unwrap();
                    responder.respond(resp);
                } else {
                    // Nessun Range: restituisci header con Accept-Ranges 
                    // ma non l'intero file (potrebbe essere enorme).
                    // Rispondiamo con 206 Partial Content per i primi bytes,
                    // così il media player sa la dimensione totale e può fare Range requests.
                    let mut file = match fs::File::open(&path) {
                        Ok(f) => f,
                        Err(e) => {
                            eprintln!("[stream] Failed to open file '{}': {}", path, e);
                            let resp = tauri::http::Response::builder()
                                .status(500)
                                .header("Content-Type", "text/plain")
                                .body(format!("Failed to open file: {}", e).into_bytes())
                                .unwrap();
                            responder.respond(resp);
                            return;
                        }
                    };

                    let max_initial = 2 * 1024 * 1024u64; // 2MB initial read
                    let read_size = (file_size).min(max_initial) as usize;
                    let mut buf = vec![0u8; read_size];
                    let bytes_read = file.read(&mut buf).unwrap_or(0);
                    buf.truncate(bytes_read);

                    eprintln!("[stream] Serving initial response for '{}': mime={}, file_size={}, bytes_sent={}", path, mime, file_size, bytes_read);

                    if (bytes_read as u64) < file_size {
                        // File più grande del chunk iniziale: rispondi con 206 Partial Content
                        let actual_end = bytes_read as u64 - 1;
                        let resp = tauri::http::Response::builder()
                            .status(206)
                            .header("Content-Type", mime)
                            .header("Accept-Ranges", "bytes")
                            .header("Content-Range", format!("bytes 0-{}/{}", actual_end, file_size))
                            .header("Content-Length", bytes_read.to_string())
                            .body(buf)
                            .unwrap();
                        responder.respond(resp);
                    } else {
                        // File piccolo: restituisci tutto con 200
                        let resp = tauri::http::Response::builder()
                            .status(200)
                            .header("Content-Type", mime)
                            .header("Accept-Ranges", "bytes")
                            .header("Content-Length", bytes_read.to_string())
                            .body(buf)
                            .unwrap();
                        responder.respond(resp);
                    }
                }
            });
        })
        .manage(Mutex::new(SyncState::default()) as AppSyncState)
        .manage(Mutex::new(TranslateState::default()) as AppTranslateState)
        .manage(Mutex::new(FlashcardState::default()) as AppFlashcardState)
        .manage(Mutex::new(TranscribeState::default()) as AppTranscribeState)
        .manage(MediaServerPort(port))
        .invoke_handler(tauri::generate_handler![
            get_media_server_port,
            // Comandi app info
            get_app_info,
            // Comandi traduzione
            set_api_config,
            load_srt_for_translate,
            start_translation,
            cancel_translation,
            get_latest_translated_subtitles,
            // Comandi sincronizzazione
            sync_load_srt,
            sync_set_video,
            sync_get_status,
            sync_get_subtitles,
            sync_get_subtitles_range,
            sync_get_subtitle,
            sync_find_subtitle_at_time,
            sync_find_nearest_subtitle,
            sync_add_anchor,
            sync_remove_anchor,
            sync_get_anchors,
            sync_suggest_next,
            sync_set_strategy,
            sync_save_file,
            sync_save_session,
            sync_load_session,
            sync_reset,
            // Comandi flashcard
            flashcard_load_subs,
            flashcard_preview,
            flashcard_generate,
            flashcard_cancel,
            flashcard_check_deps,
            flashcard_check_dir_exists,
            flashcard_get_cpu_count,
            // Comandi trascrizione
            transcribe_check_backends,
            transcribe_list_models,
            transcribe_download_model,
            transcribe_uninstall_model,
            transcribe_start,
            transcribe_cancel,
            transcribe_check_file_exists,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
