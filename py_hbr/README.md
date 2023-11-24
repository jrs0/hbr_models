# Python Library

This folder contains the python interface to the Rust library.

## Development on Windows

Install [rustup](https://www.rust-lang.org/tools/install) as per the instructions on Windows. 

Install [Python 3.9 or later](https://www.python.org/downloads/release/python-390/). Note that this code was tested in a virtual environment (create using `pip -m venv venv`), using Python 3.9. Note that `polars` was found not to work yet with Python 3.11, due to a dependency issue with `connectorx` (latest version does not have a precompiled package for that python version). The issue will likely be resolved in future.

Install the [maturin](https://github.com/PyO3/maturin) development tools using `pip install maturin`. 

To build the python package for development purposes, change to the `py_hbr` folder (this one) and run:

```powershell
maturin develop
```

If you find that you get Rust build errors after changing Python environment (or version), run `cargo clean` from the same directory and try again.

Once you have run `maturin develop`, a temporary copy of the library is installed in the current virtual environment, meaning that it can be loaded from a script as if it were an installed library. To use the library, run (for example):

```python
from py_hbr.clinical_codes import get_codes_in_group
```

## Installation on Windows

To install the library in a virtual environment in VS Code, activate the environment, change to this folder, and build the release library using:

```powershell
# -i python is required so that it looks for a binary called python (not python3), as in the venv.
maturin build --release -i python
```

This will create a wheel with a name like `target\wheels\py_hbr-0.1.0-cp39-none-win_amd64.whl`. To install it, run

```powershell
pip install target\wheels\py_hbr-0.1.0-cp39-none-win_amd64.whl
```


## Development on Linux

Install rustup according to the [instructions](https://www.rust-lang.org/tools/install) for Linux. Install python dependencies as follows:

```bash
sudo apt install python3 python3-venv unixodbc-dev
```

Create a virtual environment using, and activate it:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install maturin using `pip install maturin[patchelf]` (the `patchelf` feature prevents warnings about setting `rpath`). For developing, run `maturin develop` in the `py_hbr` folder.

## Notes

Package dependencies were checked using [deptry](https://github.com/fpgmaas/deptry):

```bash
# Install
pip install deptry
# Check the package
cd py_hbr
deptry .
```

Only dependency is currently `pandas` (ignoring false-positive warning for `py_hbr`).

Created the base [Github action](https://github.com/PyO3/maturin-action) configuration by running:

```bash
cd py_hbr
maturin generate-ci github > ../.github/workflows/py_hbr_package.yml
```