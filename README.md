# Bleeding/Ischaemia models for High Bleeding Risk

This repository contains prototype tools and scripts for creating models for bleeding and ischaemia outcomes in patients with ACS, based on the BNSSG HES data and SWD. Specifically, it contains
- a tool for creating groups of ICD-10 and OPCD-4 codes which can directly interface to the dataset generating scripts
- a set of scripts for obtaining datasets for modelling bleeding and ischaemia outcomes, and fitting models
- a quarto document which presents a comparison of the models for each dataset

## Set up using Windows

This section describes how to set up all the necessary prerequisites for development using Windows.

## VS Code Setup

This repository was developed using Visual Studio Code; using it will probably give you the highest chance of successfully getting things working. Download and install VS Code from [here](https://code.visualstudio.com/). You don't need administrative rights. Let it choose the default location, and leave all installation options on defaults.

You want a number of extensions. Install:
- Python (tested v2023.20.0), which contains multiple python linting and other tools
-  

## Python Installation

Development was undertaken using a Python 3.9.0 installation, located in `c:\users\user.name\AppData\Local\Programs\Python\Python39`, using a VS-code created virtual encironment (venv, not conda env). Python 3.10 was also verified to work, but 3.11 is too recent if you want to try using polars. (As it stands, nothing in the scripts depends on that.) I would recommend installing Python 3.10. Multiple Python installations can coexist in the `Python` folder.

Navigate to [this page](https://www.python.org/downloads/release/python-3100/), and click the `Windows Installer (64-bit)`, and run it. If you don't have admin rights, uncheck the option to install for all users (probably do this anyway). Enable the option to add Python 3.10 to the path. Click `Install Now`.

## Set up using Linux

The code will run on Linux. Use the following instructions as the basis for setting up build dependencies. Building was tested in an Ubuntu 22.04 LTS environment using docker, but database access, dataset generation and modelling was not tested.

The docker image was created using

```bash
docker run -it --name test_container ubuntu
# Ctrl-C to exit
docker start test_container
docker exec -it test_container /bin/bash
# Now in the docker container...
cat /etc/lsb-release # to confirm
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
apt install git python3 python3-venv
```

Clone this git repository using

```bash
git clone https://github.com/jrs0/hbr_models.git
```
