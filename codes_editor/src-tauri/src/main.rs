
#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use tauri_api::dialog::{select, save_file, Response};

use clap::Parser;
use tauri::Manager;

/// Search for a pattern in a file and display the lines that contain it.
#[derive(Parser)]
struct Cli {
    /// The pattern to look for
    name: Option<String>,
    /// The path to the file to read
    path: Option<std::path::PathBuf>,
}

#[tauri::command]
fn get_yaml() -> String {
    let result = match select(Some("yaml"), Some("~")) {
	Ok(response) => match response {
	    Response::Okay(s) => s,
	    _ => return String::from("{\"error\": \"other_error\"}")
	},
	Err(_) => return String::from("{\"error\": \"dialog_cancelled\"}"),
    };
    let f = std::fs::File::open(result).expect("Error reading file");
    let d: serde_json::Value = serde_yaml::from_reader(f).expect("Error parsing YAML");
    // let s = d.to_string();
    
    format!("{d}")
}

#[tauri::command]
fn save_yaml(top_level_category: serde_yaml::Value) {
    let result = match save_file(Some("yaml"), Some("~")) {
	Ok(response) => match response {
	    Response::Okay(s) => s,
	    _ => return,
	},
	Err(_) => return,
    };

    let s: String = serde_yaml::to_string(&top_level_category)
	.expect("Failed converting to string");
    std::fs::write(result, s).expect("Failed writing to file")
}


fn main() {

    let cli = Cli::parse();

    // You can check the value provided by positional arguments, or option arguments
    if let Some(name) = cli.name.as_deref() {
        println!("Value for name: {}", name);
	return;
    }

    if let Some(path) = cli.path.as_deref() {
        println!("Value for config: {}", path.display());
	return
    }
    
    tauri::Builder::default()
        .setup(|app| {
	    let main_window = app.get_window("main").unwrap();
	    main_window.eval(&format!(
		"window.location.replace('icd')"))
		.expect("Failed to navigate to icd page");
	    Ok(())
	})
        .invoke_handler(tauri::generate_handler![get_yaml, save_yaml])
	.run(tauri::generate_context!())
	.expect("error while running tauri application");

    
}
