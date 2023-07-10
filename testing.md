# Testing Plan

All code that preprocesses data will be tested on synthetic data, that matches the form of the real data (both the schema and the characteristics of the data found in the columns).

Synthetic data will not be stored in the repository. Instead, it will be generated using a seed. This keeps the repository itself lightweight, while enabling extensive testing both locally and in CI using potentially large testing sets.

Since the data is generated each time tests are run, there is no need to store the data to files. However, storing data may be helpful in order to have a hard copy of the data used for debugging purposes, or if the data generation process is long. 

This file describes the specification of the synthetic data sources that are used as part of the testing. Synthetic data sets are in the format of tables, matching the true SQL Server data format. In the program, data is loaded into an arrow record batch format from either a real SQL Server database (or other real database), or is generated synthetically. The premise of the testing is that the unit-under-test operates on the resulting record batch, so that correct processing of the synthetic record batch provides evidence for correct functioning on the non-synthetic version.

## Synthetic Data Overview

The columns in the synthetic and real data sources have columns of the following semantic types:
* **Dates and times** indicating, for example, when a hospital activity occurred or when a test was performed. Sometimes the time is included but only a date is intended (i.e. midnight 00:00 is included), and sometimes the time contains non-trivial information
* **Clinical codes** including ICD-10 and OPCS-4. These codes may be variable length strings with an ill-defined format,  
* **Patient IDs** including anonymised versions of NHS numbers. Could be numbers (stored as unsigned integers or strings), or may contain text.
* **Measurements** including laboratory test results in numerical format. Values may also come with a unit column, which could be text or enum, and may also come with a range.
* **Demographic information** including age, gender, ethnic origin, etc. The format of these columns could be text or numbers.

Columns contain NULLs, which can have meanings other than missing data. Data that come with an index (for example, secondary diagnosis columns) may use a single row and multiple columns (one per index), or use multiple rows, and two columns (one to indicate the index and the second to indicate the value). 

