//! Shabrang Desktop Shell - SOS Native Application
//!
//! This is the Tauri backend for the Shabrang desktop shell.
//! It manages the SOS sidecar (Docker) and provides IPC commands.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::process::Command;

/// SOS service status
#[derive(Debug, Serialize, Deserialize)]
struct SOSStatus {
    engine: bool,
    redis: bool,
    memory: bool,
    economy: bool,
}

/// Start SOS services via Docker Compose
#[tauri::command]
async fn start_sos(docker: bool) -> Result<String, String> {
    if docker {
        let output = Command::new("docker-compose")
            .args(["up", "-d"])
            .current_dir(get_sos_path())
            .output()
            .map_err(|e| e.to_string())?;

        if output.status.success() {
            Ok("SOS services started".to_string())
        } else {
            Err(String::from_utf8_lossy(&output.stderr).to_string())
        }
    } else {
        // Native Python mode (for development)
        Ok("Native mode not yet implemented".to_string())
    }
}

/// Stop SOS services
#[tauri::command]
async fn stop_sos() -> Result<String, String> {
    let output = Command::new("docker-compose")
        .args(["down"])
        .current_dir(get_sos_path())
        .output()
        .map_err(|e| e.to_string())?;

    if output.status.success() {
        Ok("SOS services stopped".to_string())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).to_string())
    }
}

/// Get SOS service status
#[tauri::command]
async fn get_sos_status() -> Result<SOSStatus, String> {
    // Check each service by hitting health endpoints
    let client = reqwest::Client::new();

    let engine = client
        .get("http://localhost:8000/health")
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false);

    let redis = Command::new("redis-cli")
        .args(["ping"])
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false);

    Ok(SOSStatus {
        engine,
        redis,
        memory: false,  // TODO: Add memory service check
        economy: false, // TODO: Add economy service check
    })
}

/// Open service logs
#[tauri::command]
async fn open_logs(service: String) -> Result<String, String> {
    let output = Command::new("docker-compose")
        .args(["logs", "--tail", "100", &service])
        .current_dir(get_sos_path())
        .output()
        .map_err(|e| e.to_string())?;

    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}

/// Get SOS project path
fn get_sos_path() -> String {
    std::env::var("SOS_PATH").unwrap_or_else(|_| "/home/mumega/SOS".to_string())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            start_sos,
            stop_sos,
            get_sos_status,
            open_logs
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
