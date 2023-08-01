# Python Library

This folder contains the python interface to the Rust library.

## Development on Windows

Install [rustup](https://www.rust-lang.org/tools/install) as per the instructions on Windows. 

Install [Python 3.9 or later](https://www.python.org/downloads/release/python-390/). Note that this code was tested in a virtual environment (create using `pip -m venv venv`), using Python 3.9. Note that `polars` was found not to work yet with Python 3.11, due to a dependency issue with `connectorx` (latest version does not have a precompiled package for that python version). The issue will likely be resolved in future.

Install the [maturin](https://github.com/PyO3/maturin) development tools using `pip install maturin`. 

To build the python package for development purposes, change to the `py_hic` folder (this one) and run:

```powershell
maturin develop
```

If you find that you get Rust build errors after changing Python environment (or version), run `cargo clean` from the same directory and try again.

To use the library, run (for example):

```python
from py_hic.clinical_codes import get_codes_in_group
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

Install maturin using `pip install maturin`. For developing, run `maturin develop` in the `py_hic` folder.


