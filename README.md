# Bleeding/Ischaemia models for High Bleeding Risk

This repository contains prototype tools and scripts for creating models for bleeding and ischaemia outcomes in patients with ACS, based on the BNSSG HES data and SWD. Specifically, it contains
- a tool for creating groups of ICD-10 and OPCD-4 codes which can directly interface to the dataset generating scripts
- a set of scripts for obtaining datasets for modelling bleeding and ischaemia outcomes, and fitting models
- a quarto document which presents a comparison of the models for each dataset

## Set up using Windows

This section describes how to set up all the necessary prerequisites for development using Windows.

### VS Code Setup

This repository was developed using Visual Studio Code; using it will probably give you the highest chance of successfully getting things working. Download and install VS Code from [here](https://code.visualstudio.com/). You don't need administrative rights. Let it choose the default location, and leave all installation options on defaults.

You might want a number of extensions:
- Python (tested v2023.20.0), which contains multiple python linting and other tools
-  

### Python Installation

Development was undertaken using a Python 3.9.0 installation, located in `c:\users\user.name\AppData\Local\Programs\Python\Python39`, using a VS-code created virtual encironment (venv, not conda env). Python 3.10 was also verified to work, but 3.11 is too recent if you want to try using polars. (As it stands, nothing in the scripts depends on that.) I would recommend installing Python 3.10. Multiple Python installations can coexist in the `Python` folder.

Navigate to [this page](https://www.python.org/downloads/release/python-3100/), and click the `Windows Installer (64-bit)`, and run it. If you don't have admin rights, uncheck the option to install for all users (probably do this anyway). Enable the option to add Python 3.10 to the path. Click `Install Now`.

### Rust Installation

The Rust toolchain is required to build the parts of the library written in Rust. Before installing the toolchain on Windows, you will need some build prerequisites. As described [here](https://learn.microsoft.com/en-us/windows/dev-environment/rust/setup), they can be obtained by installing Visual Studio Community, or by installing [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) (which is simpler). When you run the installer, ensure you tick the option to install the C++ tools for desktop app development. If you do find the installation didn't work, you will get a message in the rustup installation (next step) that the C++ build tools are missing. If you get that error, go back and ensure the C++ build tools are installed correctly.

Next, download the toolchain (the `rustup` tool, which installs the toolchain) from [here](https://www.rust-lang.org/tools/install). 

## Set up using Linux

The code will run on Linux. Use the following instructions as the basis for setting up build dependencies. Building was tested in an Ubuntu 22.04 LTS environment using docker, but database access, dataset generation and modelling was not tested.

The docker image was created using

```bash
docker run -it --name test_container ubuntu
# Ctrl-C to exit
docker start test_container
docker exec -it test_container /bin/bash
# Now in the docker container...
cat /etc/lsb-release # to confirm Ubuntu version, output below:
# DISTRIB_ID=Ubuntu
# DISTRIB_RELEASE=22.04
# DISTRIB_CODENAME=jammy
# DISTRIB_DESCRIPTION="Ubuntu 22.04.2 LTS"
```

The following instructions can be run in any Ubuntu-based Linux distribution (for example, Linux Mint), based on Ubuntu 22.04 LTS. If using a regular linux distribution, Run `apt` commands using `sudo`.

Install the following dependencies:

```bash
# Prefix sudo if using a regular user (if not using docker)
apt update
apt install git curl python3 python3-venv gcc clang pkg-config libssl-dev libkrb5-dev
```

Clone this git repository using

```bash
git clone https://github.com/jrs0/hbr_models.git
```

### Rust Installation

The Rust toolchain can be installed on Linux following the instructions [here](https://forge.rust-lang.org/infra/other-installation-methods.html#other-ways-to-install-rustup) and running:

```bash
# This line does not need sudo on docker or a regular linux distribution
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Follow through the interactive steps, picking all the default choices. After the installation finishes, restart your shell. Try running `cargo` to check the installation worked. If the command is not found, check that `~/.cargo/bin` is on the `PATH`, and check that the location contains the Rust installation (`cargo`, `rustc`, etc.)

Once the installation is complete, you can check the `rust_hbr` library builds by running (from the top level of the repository):

```bash
cd rust_hbr
cargo build
# Finished dev [unoptimized + debuginfo] target(s) in ...
```

### Python Library Installation

Python should be installed already as per the dependencies above (the `apt` command). It is recommended to work within a virtual environment. Create it by running (from the top level of this repository):

```bash
# This line only needs to be run once to create the environment
python3 -m venv venv

# This line should be run every time you want to start the environment in a console
source venv/bin/activate
```

All subsequent commands assume the virtual environment has been activated.

To build and install the `py_hbr` library, first install `maturin` (the build system):

```bash
# the `patchelf` feature prevents warnings about setting `rpath` later
pip install maturin[patchelf]
```

Ensure that the Rust toolchain is installed as per the steps above. To build the python package for development purposes, run:

```bash
cd py_hbr
maturin develop
```

This should install `py_hbr` into the current virtual environment. You can check it worked by running

```bash
python
# Now inside the python shell
>>> from py_hbr.clinical_codes import get_codes_in_group
```

If that works, then the library has been successfully built and installed for development purposes, and scripts that rely on `py_hbr` should run correctly. 

You can also build and install a release version of the library, which will compile the Rust code with optimisations turned on. This may be helpful if you need to call the code in a way where performance might be a problem. Be aware that the Rust code has not be profiled and optimised, so substantial performance improvements are likely possible.

To build in release mode, run the following command:

```bash
maturin build --release
```

This will create a wheel with a name like `target/wheels/py_hbr-0.1.0-cp310-cp310-manylinux_2_34_x86_64.whl`. To install it into the current virtual environment, run

```bash
# You may need to add --force-reinstall onto the end if you previously ran `maturin develop`
pip install target/wheels/py_hbr-0.1.0-cp310-cp310-manylinux_2_34_x86_64.whl
```

See the [Maturin documentation](https://github.com/PyO3/maturin) for more information about how to build and install the library.

### R Library Installation

These instructions were tested on the Ubuntu docker image above and Linux Mint 21.1. Install R and other package dependencies as follows (omit `sudo` if using a docker container):

```bash
# Install R
apt install r-base-core

# Install dependencies for the devtools package
apt install libcurl4-openssl-dev libfontconfig1-dev libharfbuzz-dev libfribidi-dev libfreetype6-dev libpng-dev libtiff5-dev libjpeg-dev libxml2-dev 

# Install dependencies for the Rust library
apt install unixodbc-dev
```

To install the development version of the `rhbr` package, clone this repository, navigate to the `rhbr` directory, and run `R`. Then install the package as follows:

```r
# Install devtools if not already installed
install.packages("devtools")

# Required to generate R wrappers for rust functions
devtools::document()

# Develop (import all functions into current R session)
devtools::load_all()

# Install the package locally
devtools::install()
```

You can check that the library installed correctly by trying to load it using `library(rhbr)`.