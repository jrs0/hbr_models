# R Library

This folder contains the R interface to the underlying rust library. It provides access to the data sources (from a real SQL Server), or the synthetic data for testing/development purposes

## Installation on Windows

TODO: get installation/development working on windows and document steps.

## Installation on Linux

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

