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

## Data source connection and data processing

Ideally, a single library should connect to the two required data sources (SQL Server and SQLite). Using a different library for SQLite vs. SQL Server reduces the effectiveness of the SQLlite-based testing, because a substantial part of the code could differ between the two implementations.

The Rust crate [sqlx](https://crates.io/crates/sqlx) supports both, but it does not seem possible to use data-source-name-based connection strings, or active-directory-based authentication to connect to the database. In addition, the SQL Server support was only recently added, does not support encryption, and appears to be being moved to a proprietory license (see [here](https://stackoverflow.com/questions/70032527/connecting-to-sql-server-with-sqlx)). For simplicity in Windows, an ODBC-based driver would be preferable, because it will support ODBC-style connection strings (in particular, domain source names). 

Another approach is to use a framework such as Arrow, and convert all the (unprocessed) data sources into this format first. Arrow supports an ODBC connection library [arrow-odbc](https://crates.io/crates/arrow-odbc), which [supports the odbc connection sytax](https://docs.rs/arrow-odbc/latest/arrow_odbc/). SQLite support is not clear, however, Arrow itself (more specifically, [Parquet](https://parquet.apache.org/)), may be a more easily-integrated format for testing. This way, the tests can be written at the Arrow level, using either data from the SQL Server source or synthetic data in a file.

Arrow can be used with multiple other data source, via [ConnectorX](https://docs.rs/connectorx/latest/connectorx/). ConnectorX also support SQL Server, however, it is not clear whether ODBC connection strings are supported; if they are, then ConnectorX can be used in place of `arrow-odbc`.

Once an SQL Server datasource has been read into an Arrow in-memory representation using `arrow-odbc`, [this function](https://docs.rs/datafusion/latest/datafusion/execution/context/struct.SessionContext.html#method.register_batch) from [Datafusion](https://arrow.apache.org/datafusion/) can be used to create a dataframe object, on which SQL-like queries can be performed (such as joins, filters, etc.). This can be used as the basis for an in-memory dataframe structure that is a copy of the data in the original datasource in its unpreprocessed state. At this point, both synthetic data and SQL Server data would be represented in the same way (synthetic data can come from [this function](https://docs.rs/datafusion/latest/datafusion/execution/context/struct.SessionContext.html#method.register_parquet) which reads a dataframe from Parquet), and can form the basis for a test suite that checks the preprocessing.














