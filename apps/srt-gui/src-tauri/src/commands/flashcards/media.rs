use anyhow::{Context as _, Result};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::io::Write;
use std::path::{Path, PathBuf};
use tauri::{AppHandle, Emitter, State};
use tokio_util::sync::CancellationToken;
use crate::state::AppFlashcardState;

use super::types::*;
use super::parser::*;
use super::matcher::*;
use super::filters::*;

use super::export_tsv::*;
use super::export_apkg::*;

// ─── FFmpeg Media Extraction ─────────────────────────────────────────────────

/// Check if ffmpeg is available
pub(crate) async fn check_ffmpeg() -> Result<bool> {
    let output = tokio::process::Command::new("ffmpeg")
        .arg("-version")
        .output()
        .await;
    Ok(output.is_ok())
}

/// Format milliseconds as ffmpeg timestamp HH:MM:SS.mmm
pub(crate) fn ms_to_ffmpeg_ts(ms: i64) -> String {
    let ms = ms.max(0);
    let total_secs = ms / 1000;
    let millis = ms % 1000;
    let secs = total_secs % 60;
    let mins = (total_secs / 60) % 60;
    let hours = total_secs / 3600;
    format!("{:02}:{:02}:{:02}.{:03}", hours, mins, secs, millis)
}

/// Extract audio clip for a single subtitle line
pub(crate) async fn extract_audio_clip(
    source_path: &str,
    output_path: &Path,
    start_ms: i64,
    end_ms: i64,
    pad_start_ms: i64,
    pad_end_ms: i64,
    bitrate: u32,
) -> Result<()> {
    let actual_start = (start_ms - pad_start_ms).max(0);
    let duration_ms = (end_ms + pad_end_ms) - actual_start;

    let mut cmd = tokio::process::Command::new("ffmpeg");
    cmd.args([
        "-nostdin",
        "-loglevel", "error",
        "-y",
        "-ss", &ms_to_ffmpeg_ts(actual_start),
        "-t", &ms_to_ffmpeg_ts(duration_ms),
        "-i", source_path,
        "-vn", "-sn", "-dn",
        "-ac", "2",
        "-ab", &format!("{}k", bitrate),
        "-ar", "44100",
        "-f", "mp3",
    ]);
    cmd.arg(output_path.as_os_str());

    let output = cmd.output().await.context("Failed to run ffmpeg for audio")?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        anyhow::bail!("ffmpeg audio error: {}", stderr);
    }
    Ok(())
}

/// Extract snapshot at midpoint of subtitle
pub(crate) async fn extract_snapshot(
    video_path: &str,
    output_path: &Path,
    start_ms: i64,
    end_ms: i64,
    width: u32,
    height: u32,
    crop_bottom: u32,
) -> Result<()> {
    let midpoint_ms = start_ms + (end_ms - start_ms) / 2;

    let mut vf_filters = Vec::new();
    if crop_bottom > 0 {
        vf_filters.push(format!("crop=in_w:in_h-{}:0:0", crop_bottom));
    }
    vf_filters.push(format!("scale={}:{}:flags=bicubic", width, height));
    let vf = vf_filters.join(",");

    let mut cmd = tokio::process::Command::new("ffmpeg");
    cmd.args([
        "-nostdin",
        "-loglevel", "error",
        "-y",
        "-ss", &ms_to_ffmpeg_ts(midpoint_ms),
        "-i", video_path,
        "-an", "-sn", "-dn",
        "-vframes", "1",
        "-vf", &vf,
        "-pix_fmt", "yuvj420p",
        "-q:v", "2",
    ]);
    cmd.arg(output_path.as_os_str());

    let output = cmd.output().await.context("Failed to run ffmpeg for snapshot")?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        anyhow::bail!("ffmpeg snapshot error: {}", stderr);
    }
    Ok(())
}

/// Extract video clip for a single subtitle line
pub(crate) async fn extract_video_clip(
    video_path: &str,
    output_path: &Path,
    start_ms: i64,
    end_ms: i64,
    pad_start_ms: i64,
    pad_end_ms: i64,
    codec: &str,
    preset: &str,
    video_bitrate: u32,
    audio_bitrate: u32,
) -> Result<()> {
    let actual_start = (start_ms - pad_start_ms).max(0);
    let duration_ms = (end_ms + pad_end_ms) - actual_start;

    let mut cmd = tokio::process::Command::new("ffmpeg");
    cmd.args([
        "-nostdin",
        "-loglevel", "error",
        "-y",
        "-ss", &ms_to_ffmpeg_ts(actual_start),
        "-t", &ms_to_ffmpeg_ts(duration_ms),
        "-i", video_path,
    ]);

    match codec {
        "h264" => {
            cmd.args([
                "-c:v", "libx264",
                "-preset", preset,
                "-b:v", &format!("{}k", video_bitrate),
                "-c:a", "aac",
                "-b:a", &format!("{}k", audio_bitrate),
            ]);
        }
        _ => {
            // mpeg4
            cmd.args([
                "-c:v", "mpeg4",
                "-b:v", &format!("{}k", video_bitrate),
                "-c:a", "mp3",
                "-b:a", &format!("{}k", audio_bitrate),
            ]);
        }
    }

    cmd.arg(output_path.as_os_str());

    let output = cmd.output().await.context("Failed to run ffmpeg for video clip")?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        anyhow::bail!("ffmpeg video error: {}", stderr);
    }
    Ok(())
}

/// Normalize audio volume using ffmpeg loudnorm
pub(crate) async fn normalize_audio(file_path: &Path) -> Result<()> {
    let temp_path = file_path.with_extension("normalized.mp3");

    let mut cmd = tokio::process::Command::new("ffmpeg");
    cmd.args([
        "-y",
        "-i",
    ]);
    cmd.arg(file_path.as_os_str());
    cmd.args([
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-ar", "44100",
        "-ac", "2",
    ]);
    cmd.arg(temp_path.as_os_str());

    let output = cmd.output().await.context("Failed to normalize audio")?;
    if output.status.success() {
        std::fs::rename(&temp_path, file_path)?;
    } else {
        let _ = std::fs::remove_file(&temp_path);
    }
    Ok(())
}

