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

The following sections contain specifications for example synthetic tables. Discrepencies between the types of columns and the semantic content (for example, a nullable column that cannot be null, and behaves as a primary key) is due to the requirement to copy as closely as possible real datasets for testing purposes. Column descriptions clarify the actual content of the column.

### Blood test results table: `pathology_blood`

This table contains blood test results.

Columns, SQL Server types, and descriptions:
* `subject`, nvarchar(30), nullable: contains a string in the form `bristol_<NUM>`, where `<NUM>` is a four or five digit unsigned integer without leading zeros. Represents the patient id. Does not contain nulls.
* `laboratory_department`, nvarchar(30), nullable: always NULL in this synthetic data.
* `order_name`, nvarchar(100), nullable: top-level test category, capitalised (e.g. "FULL BLOOD COUNT"). Does not contain nulls.
* `test_name`, nvarchar(100), nullable: laboratory test name, lower-case (e.g. "haemoglobin"). Does not contain nulls.
* `test_result`, nvarchar(200), nullable: laboratory test result. Often a floating-point number or an integer. Often less than 6 characters in total. Can containg inequalities (e.g. "<5"). Does not contain units. Does not contain nulls.
* `test_result_unit`, nvarchar(40), nullable: the physical unit of the test result, or null if the test result is dimensionless. For example, "nmol/L", "10*9/L" (meaning "1e9/L"), "s", etc.
* `sample_collected_date_time`, datetime, nullable: date/time blood sample collected (from the patient), resolution to the minute, does not contain nulls.
* `result_available_date_time`, datetime, nullable: date/time from which result was available, resolution to the minute, does not contain nulls.
* `result_flag`, nvarchar(40), nullable: flag indicating high/low result; values either "<" or null. Unknown interpretation.
* `result_lower_range`, nvarchar(100), nullable: lower normal result range. Value with the same format as `test_result`. May be null.
* `result_upper_range`, nvarchar(100), nullable: upper normal result range. Value with the same format as `test_result`. May be null.
* `brc_name`, nvarchar(10), nullable: name of source of test information. Always equal to "bristol". Does not contain nulls.




