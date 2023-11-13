# Base Rust Library

This is the backend rust library that contains the synthetic data generation and main data preprocessing. The use of rust is motivated by portability, speed, and the ability to interface with R, python and the Tauri application development framework.

## Installation on Windows

Main development is performed on Windows. Make sure rust is installed as per the rustup installation instructions for Windows. 

TODO: write detailed instructions for development environment setup using vscode.

## Installation on Linux

Install rust following the latest [installation instructions](https://www.rust-lang.org/tools/install) (use rustup). You also need to install unixodbc for connection to Microsoft SQL Server:

```bash
sudo apt install unixodbc-dev
```

