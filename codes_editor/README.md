# Code group editor

This folder contains the program for creating groups of ICD-10 and OPCS-4 codes.

## Developer Dependencies (Linux)

```bash
# To install system dependencies (Ubuntu 22.04 LTS)
sudo apt install libgtk-3-dev libsoup-gnome2.4-dev libjavascriptcoregtk-4.0-dev libwebkit2gtk-4.0-dev
```

## Rust Dependencies

Install rustup according to your platforms method.

## Node Dependencies

```bash
# To install node dependencies
npm install
 ```

The command to develop is `cargo tauri dev`. The command to build the release version is `cargo tauri build`. The resulting binary will be located in `src-tauri\target\release\map-editor.exe`
