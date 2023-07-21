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

Alternative languages were also considered. For example, the use of Java would potentially enable the use of the open-source system [OpenEHR](https://openehr.org/) to avoid constructing an internal data storage format like the `Patient` struct (see below). However, the other requirements (interface to R and python), the relative simplicity of the internal data being stored, and lack of developer expertise in Java, informed the choice for Rust. A further iteration of the project could convert the codebase to use a fully-featured system such as OpenEHR, after an initial proof-of-concept.

### Programming Language Infrastructure

The repository contain a library for the backend written in Rust, frontends that use the Rust library, and interfaces to the backend from R and Python. One of the advantages of the Rust cargo crate system is that git-url dependencies will look anywhere in the referenced git repository for the crate (see [the cargo documentation](https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html#specifying-dependencies-from-git-repositories)), meaning that the main Rust backend library does not need to be at the root. As a result, each application that is part of the project can occupy a folder at the top level of this repository. 

R and Python both have libraries that allow interfacing to Rust crates using a `Cargo.toml`, which can reference this repository. This will mean that the dependencies for the libraries in those languages will work anywhere by provided the git url is correct (in particular, both locally and CI). Tauri (for frontends) also uses a `Cargo.toml` and will work in the same way.

With all the code is in the same git repository, it is much easier to define a consistent synchronised state of all the packages, that can be guaranteed to work together at a particular commit and is more easily be signed off as tested.

## Data source connection and data processing

Ideally, a single library should connect to the two required data sources (SQL Server and SQLite). Using a different library for SQLite vs. SQL Server reduces the effectiveness of the SQLlite-based testing, because a substantial part of the code could differ between the two implementations.

The Rust crate [sqlx](https://crates.io/crates/sqlx) supports both, but it does not seem possible to use data-source-name-based connection strings, or active-directory-based authentication to connect to the database. In addition, the SQL Server support was only recently added, does not support encryption, and appears to be being moved to a proprietory license (see [here](https://stackoverflow.com/questions/70032527/connecting-to-sql-server-with-sqlx)). For simplicity in Windows, an ODBC-based driver would be preferable, because it will support ODBC-style connection strings (in particular, domain source names). 

Another approach is to use a framework such as Arrow, and convert all the (unprocessed) data sources into this format first. Arrow supports an ODBC connection library [arrow-odbc](https://crates.io/crates/arrow-odbc), which [supports the odbc connection sytax](https://docs.rs/arrow-odbc/latest/arrow_odbc/). SQLite support is not clear, however, Arrow itself (more specifically, [Parquet](https://parquet.apache.org/)), may be a more easily-integrated format for testing. This way, the tests can be written at the Arrow level, using either data from the SQL Server source or synthetic data in a file.

Arrow can be used with multiple other data source, via [ConnectorX](https://docs.rs/connectorx/latest/connectorx/). ConnectorX also support SQL Server, however, it is not clear whether ODBC connection strings are supported; if they are, then ConnectorX can be used in place of `arrow-odbc`.

Once an SQL Server datasource has been read into an Arrow in-memory representation using `arrow-odbc`, [this function](https://docs.rs/datafusion/latest/datafusion/execution/context/struct.SessionContext.html#method.read_batch) from [Datafusion](https://arrow.apache.org/datafusion/) can be used to create a dataframe object, on which SQL-like queries can be performed (such as joins, filters, etc.). This can be used as the basis for an in-memory dataframe structure that is a copy of the data in the original datasource in its unpreprocessed state. At this point, both synthetic data and SQL Server data would be represented in the same way (synthetic data can come from [this function](https://docs.rs/datafusion/latest/datafusion/execution/context/struct.SessionContext.html#method.register_parquet) which reads a dataframe from Parquet), and can form the basis for a test suite that checks the preprocessing.

## Patient Data Model

The central data structure in the Rust library (which is the core part of the codebase) is the Patient structure. The idea is to create a `struct` in Rust that contains all the information that is wanted about a patient, including demographic information, hospital activity (spells and episodes), comorbidities (either inferred from hospital episode diagnoses or taken from primary care datasets), laboratory tests and results, and prescriptions information. 

Data in the Patient struct is populated from any data source (it could be an SQL Server, or APIs connected to the systems that hold the data). The key is that preprocessing steps have been performed which make a guarantee about the validity of the data, so that once it is in the Patient struct it can be trusted to be valid.

It is more appropriate to store the Patient struct in a document-oriented database, such as MongoDB, because that avoids the need to design a normalised database schema independenty of designing the struct itself. Rust has tools (e.g., [the MongoDB Rust library with serde](https://www.mongodb.com/developer/languages/rust/rust-mongodb-crud-tutorial/)) that can automatically serialise the Patient struct in a format suitable for storage in a database. This could form the basis for a deployed solution, where information is pulled from multiple sources and stored locally in a database. 

The data in the Patient struct is used for two purposes: processing into derived dataset (back in tabular format) for use in the higher level Rust and Python libraries, which can make use of the vast array of packages for data analysis using the data.

In addition, the data can be viewed directly in a frontend (such as a Tauri application, or any other web framework that interfaces with Rust) for the purpose of viewing patient data in one place. This is useful both for analysis (to provide a interactive way to explore the data in a readable format to inform what data analysis to do) and it could also form the basis for a deployed tool that simply presents the required information to clinicians, or presents the data along with the calculation of simple scores (such as ARC-HBR).

An advantage of using the same Rust backend for both purposes is that data analysis is being performed on the same data source (the Patient struct) that would be present in a deployment. This separates the design and testing of the front end (everything above the Patient struct; any GUIs showing data, or any model development) from the backend (which involves preprocessing data sources to generate the data required for the front end).

If models prototyped in R or Python are found to work well, they can likely be implemented in Rust, which [also has libraries for machine learning](https://github.com/vaaaaanquish/Awesome-Rust-MachineLearning), that include basics like logistic regression, decision trees, xgboost and random forests. This makes it possible to deploy a fully-Rust-based application, which would improve the simplicity and performance of the result.

In general, fields are optional in the structs below. The idea of the `Patient` struct is to gather as much information as possible, even if it is incomplete. It is up to the users of the struct to decide if a field is required, and exclude the data point as required.

For datetimes, the chrono library will be used (one of the two [official](https://blessed.rs/crates) libraries), because it is compatible with MongoDB serialisation.

The Patient struct needs the following fields:
* `id` (required): this is the field that will be used as the MongoDB unique id. It is not the NHS number or trust number. It has a specific MongoDB type `ObjectId`.
* `nhs_number` (optional, string): this field supports either the real NHS number (that could be used in a deployment), or the pseudonymised NHS number (if using a dataset like hospital episode statistics). The use of a string type provides flexibility regarding the uses of this field. It is the responsibility of the user of `Patient` to ensure that the field is in a defined and consistent format (same comment applies to trust number).
* `trust_number` (optional, string): another patient identifier, present in the hospital. This field can be null for data analysis purposes, or present for a deployment
* `age` (optional, u32): the age is a non-negative integer
* `spells` (optional, vector of `Spell`): the list of known hospital spells (as in hospital episode statistics). The field is optional, even though no spells could be indicated with an empty vector, to 
    * maintain consistency with the other fields
    * provide the flexibility for users of `Patient` to draw a semantic distinction between `None` and empty vector (e.g. `None` could mean that no episode data is available, whereas empty could mean that episode information is available, but it contains no spells)
* `mortality` (optional, type `Mortality`): information about whether the patient is alive. `None` means that the information is not available.
* `measurements` (optional, vector of `MeasurementHistory`): list of different measurements (laboratory test or other, e.g. haemoglobin or platelet count). Each `MeasurementHistory` is a time series of one type of measurement result with data source, date and value, along with metadata about the time series.
* `prescriptions` (optional, vector of `PrescriptionHistory`): list of different prescriptions (drugs or otherwise). Each `PrescriptionHistory` is a time series of one type of prescription with data source, date started, duration, and amount (if applicable), along with metadata about the time series.

The `PrescriptionsHistory` contains the following fields:
* `prescription_name` (required, string): the name of the prescription
* `unit_or_instruction` (required, string): this field is intended to explain the meaning of the value stored in the time series. For simplicity, it is a string, to support potentially non-unit qualitative prescriptions. For units, a single consistent unit will be chosen for all values in the time series, which will be normalised to this unit. For example, the unit may be chosen to be "mg/d", and then 10 mg twice daily would be expressed as 20 in the time series. This is indistinguishable from a prescription of 20 mg per day, but the compromise will simplify the code. The key is that each drug will obtain a canonical unit.
* `timeseries` (required, vector of `Prescription`): the actual prescription information, with amount, duration and date prescribed

The `Prescription` contains the following fields:
* `value` (required, enum `PrescriptionValue`): the value could either be numerical or non-numerical, hence the type
* `prescription_date` (optional, `chrono::DateTime<Utc>`): the time the presscription was made
* `duration` (optional, `chrono::Duration`): the duration of the prescription
* `data_source` (optional, enum `DataSource`): either primary care data source or secondary care data source.

The `MeasurementHistory` contains the following fields:
* `measurement_name` (required, string): the name of the measurement
* `measurmeent_unit` (required, string): the unit for the measurement. This could be replaced with a units library, but it is simpler to use a string for now to speed up prototyping.
* `timeseries`: (required, vector or `Measurement`): 

The `Measurement` contains the following fields:
* `value` (required, `MeasurementValue`): the value could either be numerical or non-numerical, hence the bespoke type.
* `measurement_date` (optional, `chrono::DateTime<Utc>`): the time the measurement was performed
* `measurement_available` (optional, `chrono::DateTime<Utc>`): the time the measurement became available to the clinician
* `data_source` (optional, enum `DataSource`): either primary care data source or secondary care data source.

The `Spells` structure contains the following fields (note no id; that is only required for `Patient` which is stored directly in the database):
* `start` (optional, `chrono::DateTime<Utc>`): the time the hospital spell started
* `end` (optional, `chrono::DateTime<Utc>`): the time the hospital spell ended
* `episodes` (optional, vector of `Episode`): the list of episodes in this spell

The `Episode` structure contains the following fields:
* `start` (optional, `chrono::DateTime<Utc>`): the time the hospital spell started
* `end` (optional, `chrono::DateTime<Utc>`): the time the hospital spell ended
* `primary_diagnosis` (optional, `DiagnosisCode`): the primary diagnosis of the episode, ICD-10
* `secondary_diagnoses` (optional, vector of `DiagnosisCode`): the secondary diagnoses of the episode, ICD-10 
* `primary_procedure` (optional, `ProcedureCode`): the primary procedure of the episode, OPCS-4
* `secondary_procedures` (optional, vector of `ProcedureCode`): the secondary procedures of the episode, OPCS-4

Both the `DiagnosisCode` and the `ProcedureCode` contain a reference (an `id`, type u64) to a `ClinicalCode`, which contains three items:
* `code` (required, string): the ICD-10 or OPCS-4 code
* `description` (required, string): the text description of the code
* `groups` (required, vector of strings): the list of groups which contain the code

Using a reference to the code allows two codes to be compared for equality, without needing to carry around their string descriptions. In the C++ prototype code [rdb](https://github.com/jrs0/rdb), it was also found that caching the codes during code parsing improved performance significantly; that is, maintaining a map from code strings found in the database to the resulting code ID. When the content of the code is required, it can be fetched using the reference.























