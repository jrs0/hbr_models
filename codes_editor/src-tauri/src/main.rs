#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

//use tauri::api::dialog::{save_file, select, Response};
//use tauri::api::dialog::FileDialogBuilder;
//use tauri::State;
//use std::sync::Mutex;
//use std::sync::Arc;

//struct AppState(Arc<Mutex<String>>);

#[tauri::command]
fn open_codes_file(file_path: &str) -> String {
    let f = std::fs::File::open(file_path).expect("Error reading file");
    let d: serde_json::Value = serde_yaml::from_reader(f).expect("Error parsing YAML");
    format!("{d}")
}

#[tauri::command]
fn save_codes_file(file_path: &str, top_level_category: serde_yaml::Value) {
    let s: String =
        serde_yaml::to_string(&top_level_category).expect("Failed converting to string");
    std::fs::write(file_path, s).expect("Failed writing to file")
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![open_codes_file, save_codes_file])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
