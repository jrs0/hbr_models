# R Library

This folder contains the R interface to the underlying Rust library. It provides access to the data sources (from a real SQL Server), or the synthetic data for testing/development purposes.

## Development on Windows

Install [rustup](https://www.rust-lang.org/tools/install) as per the instructions on Windows. You need to install a specific target for Windows and R, as follows:

```pwoershell
rustup target add x86_64-pc-windows-gnu
```

Install [R 4.3 or later](https://cran.r-project.org/bin/windows/base/) and [Rtools43](https://cran.r-project.org/bin/windows/Rtools/rtools43/rtools.html) (or the corresponding version for your version of R). To build the package, run (from an R console):

```r
# This will also build the Rust library
rextendr::document()
```

If you get the error `Could not find tools necessary to compile a package`, you may need to add the path to `rtools43` to the path. Update your `.Renviron` (located at `C:\Users\your-username\.Renviron` on Windows) as follows:

```
PATH="c:/rtools43/x86_64-w64-mingw32.static.posix/bin;c:/rtools43/usr/bin;${PATH}"
```

### Tips for Windows Development

If the rust part of the library needs recompilation, it seems faster to do it directly using `cargo build` from the `src/rust/` directory than calling `rextendr::document()` from an R console (at least on my computer). This recompilation is needed after calling `cargo update` from `src/rust`, which is required when the `rust_hic` crate changes 



## Development on Linux

These instructions were tested on Linux Mint 21.1. Install R and other package dependencies as follows:

```bash
# Install R 
sudo apt install r-base-core

# Install dependencies for the devtools package
sudo apt install libcurl4-openssl-dev libfontconfig1-dev libharfbuzz-dev libfribidi-dev libfreetype6-dev libpng-dev libtiff5-dev libjpeg-dev

# Install dependencies for the Rust library
sudo apt install unixodbc-dev
```

To install the development version of the package, clone this repository, navigate to this directory (`rhic`), and run R. Then install the package as follows:

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

