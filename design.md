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

Tauri has been used for prototyping a frontend for viewing a version of the `Patient` structure, and for selecting code groups for ICD-10 and OPCS-4 (as part of data preprocessing). Tauri (building native applications based on a rust backend) offers good performance for viewing large quantities of 




