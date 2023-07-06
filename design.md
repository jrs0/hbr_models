# Design

This document contains the overall design of the program. Design alternatives are given and the chosen approach is justified.

## Programming languages

Four requirements define the options for programming language:
* The need to support prototyping development of statistical models, machine-learning models, and risk-score calculations. 
* The need for data preprocessing which may be computationally intensive (for example, sanitising ICD-10/OPCS-4 codes)
* The need for flexible frontend development to display both the raw data structure (the `Patient` struct) and the risk-score calculation (the main example application)
* Support Windows, Mac and Linux
* Need for universal support (i.e. across all languages used) for at least Microsoft SQL Server and SQLite.
* Full interoperability between languages used (i.e. for moving data between them).
* All dependency libraries should be non-commercial and open source

Support for R and Python is required, in order to access the large set of packages for model development. 

C++ has been used to prototype some of the required preprocessing for ICD-10 and OPCS-4 codes, and interfaces to both R and Python. C++ offers the requisite speed for intensive preprocessing. However, C++ cross-platform support is challenging, especially when using modern C++ and interfacing to both R and python. C++ cross-platform dependency management is also challenging, while maintaining compatibility with R and Python build systems.

Tauri has been used for prototyping a frontend for viewing a version of the `Patient` structure, and for selecting code groups for ICD-10 and OPCS-4 (as part of data preprocessing). Tauri (building native applications based on a rust backend) offers good performance for viewing large quantities of data (e.g. all the spells for all patients).

Rust is a candidate language for the data preprocessing, because:
* it has performance comparable with C++
* it has good support for optional structures, which will be widely used in the `Patient` struct
* it has simple cross-platform support that "just works" on Windows, Mac and Linux, and provides a package manager for automatic dependency installation

In addition, it interfaces to by R and python, and a rust library can also be easily used as the backend for a Tauri application (which may itself be deployed either as a native application or as a web service). Rust's emphasis on safety, and build-system support for unit testing and integration testing (which is all cross-platform), makes it a considerably simpler option than C++.

For these reasons, Rust will be used to implement the preprocessing backend for connecting to the data sources. The Rust library will provide this data to: 
* R and Python prototyping environments, for model development and data analysis
* Tauri applications, for viewing processed patient data easily and forming the basis for the example risk-score calculation application.











