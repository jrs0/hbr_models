#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

//use tauri::api::dialog::{save_file, select, Response};
use tauri::api::dialog::FileDialogBuilder;
use tauri::State;
use std::sync::Mutex;
use std::sync::Arc;

struct AppState(Arc<Mutex<String>>);

#[tauri::command]
fn open_codes_file(app_state: State<AppState>) {
    let app_state_2 = app_state.clone();
    FileDialogBuilder::new().pick_file(move |file_path| {
        if let Some(path) = file_path {
            let f = std::fs::File::open(path).expect("Error reading file");
            let d: serde_json::Value = serde_yaml::from_reader(f).expect("Error parsing YAML");   
            *app_state_2.0.lock().unwrap() = format!("{d}");
        }
    });
}

#[tauri::command]
fn save_yaml(top_level_category: serde_yaml::Value) {
    // let result = match save_file(Some("yaml"), Some("~")) {
    //     Ok(response) => match response {
    //         Response::Okay(s) => s,
    //         _ => return,
    //     },
    //     Err(_) => return,
    // };

    // let s: String =
    //     serde_yaml::to_string(&top_level_category).expect("Failed converting to string");
    // std::fs::write(result, s).expect("Failed writing to file")
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![open_codes_file, save_yaml])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
