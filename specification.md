# Specification

This file summarises the requirements of the software in this repository, along with justification for the requirements.

## Underlying Data Sources

The data source can be a single database containing multiple tables of health-care information about patients in any format. At least Microsoft SQL Server and SQLite must be supported.

## Data Preprocessing

The core data preprocessing routines convert data from the form in the data source to an internal program structure `Patient` that stores the following information about a patient:

* **Demographics**: Age, gender, date of birth, 
* **Mortality**: If not alive, date and cause of death
* **Hospital activity**: Spells of episodes containing diagnoses and procedures
* **Laboratory tests and results**: E.g. full blood count (haemoglobin, platelets, etc.)
* **Prescriptions information**: What was prescribed, when it was prescribed, etc.

In the internal structure, any piece of information may be missing. Parts of the program that use this information as a data source are free to discard structures that are missing required data.

Preprocessing is necessary to bring data in the original data source into the correct format for `Patient`. For any piece of information `A` in the original data source that is converted to an item `B` in `Patient`, the following must hold:

1. The valid forms of `A` must be documented
2. The process `P` required to convert a valid `A` to `B` must be defined, tested, and documented

The code will hold multiple preprocessors `P`, one for each piece of information `A`. The preprocessing step should allow only data that has a particular documented format, and treat invalid/nonconforming data as missing.

The intention is that `P` is a tested, documented, and reusable preprocessing step that could also be used in a deployed application. Users (including program users) of the preprocessed information should be able to trust the validity of `A`  based on the preprocessing documentation and tests without having to see the original unprocessed form `B`.

Multiple different preprocessors can generate the same information `A` from different sources `B1`, `B2`, etc., which represents the situtation where the same (or similar) information is encoded differently in different datasets. As a result, knowing how to interpret `A` requires the documentation for the preprocessor being used to generate `A`.

## R and Python Interface

The `Patient` structure forms the basis for creating datasets of patient information. Datasets are formed by programs that read all `Patient` structures and extract information into dataframes (tables) of predictors and outcomes, for the purpose of modelling or data analysis. The results should be importable into R or Python.

Where a data valus is missing in `Patient`, the result is `NA` in the dataframe. The allowed types in the dataframe is defiend by the program that produces it. If type conversions are involved, they must be documented and tested.

## Portability 

The code should run on all three of Windows, Mac and Linux. Data analysis is often performed on Windows or Mac, and healthcare databases often use Microsoft SQL Studio. 

Deployed code may target Linux (e.g. if the code is deployed on an Ubuntu server), especially if the deployment is in the form of a web application.

## Documentation and Testing

Documentation must be included for each preprocessing function, along with tests that establish the preprocessor performs its function correctly. Documentation must be in a format that can be rendered into a static website.

All code must be covered by integration tests, which run on synthetic data stored with the code. The tests must be buildable using continuous integration. All subsystems of the code must be covered by unit tests, including all preprocessor function.

## Performance

Preprocessing functions must be high enough performance that they will not introduce observable latency into deployed applications based on them. Preprocessing throughput must be high enough to ensure timely processing of a full dataset for the purpose of the R and Python interface.















## Interface for Data Analysis/Prototyping

The 