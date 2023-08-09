# Testing Plan

All code that preprocesses data will be tested on synthetic data, that matches the form of the real data (both the schema and the characteristics of the data found in the columns).

Synthetic data will not be stored in the repository. Instead, it will be generated using a seed. This keeps the repository itself lightweight, while enabling extensive testing both locally and in CI using potentially large testing sets. 

The functions that define synthetic data are configurable, and using the same seed with different configuration will give different results. The results will also be different if the implementation of the functions changes (even if the same seed is used). As a result, a reproducable test is defined by a commit of this repository (which will include a fixed snapshot of the functions, a set of configuration arguments, and the seeds used). Test documentation will explain in detail how they are to be reproduced.

Since the data is generated each time tests are run, there is no need to store the data to files. However, storing data may be helpful in order to have a hard copy of the data used for debugging purposes, or if the data generation process is long. 

This file describes the specification of the synthetic data sources that are used as part of the testing. Synthetic data sets are in the format of tables, matching the true SQL Server data format. In the program, data is loaded into an arrow record batch format from either a real SQL Server database (or other real database), or is generated synthetically. The premise of the testing is that the unit-under-test operates on the resulting record batch, so that correct processing of the synthetic record batch provides evidence for correct functioning on the non-synthetic version.

## Reproducibility

Although the state of the synthetic data is determined by the commit and the seed used, in practice it is important that certain changes can be made to the code without causing all the synthetic data to change (provided the same seed is used). This is unavoidable at the lowest level of data generation; however, a practical case of importance is if a single new column is added to a dataset, the rest of the data should ideally remain unchanged.

To accomodate this, each block of data being generated (a list of columns) will be associated with a unique id. The global seed will be appended to this id, and the result will be cryptographically hashed to obtain the seed used to generate this block of data. Since a new random generator will be used for each such block, the following two conditions hold:
1. Each such block will be independent. This means blocks can be formed into tables, and new blocks can be added to the table without changing the already existing blocks.
2. Increasing the length (number of rows) in a block will not modify the preexisting rows.

These two properties will ensure that tests on the synthetic data are robust in the face of adding new synthetic data.

Cryptographic hashes for Rust are documented [here](https://github.com/RustCrypto/hashes#rustcrypto-hashes), which recommends BLAKE2, SHA-2 or SHA-3. BLAKE2 is used in this code.

## Testing Static Resources

When Rust crates need static files for testing, these will be located in the folder `resources/test` next to `Cargo.toml`.

## Synthetic Data Overview

The columns in the synthetic and real data sources have columns of the following semantic types:
* **Dates and times** indicating, for example, when a hospital activity occurred or when a test was performed. Sometimes the time is included but only a date is intended (i.e. midnight 00:00 is included), and sometimes the time contains non-trivial information
* **Clinical codes** including ICD-10 and OPCS-4. These codes may be variable length strings with an ill-defined format,  
* **Patient IDs** including anonymised versions of NHS numbers. Could be numbers (stored as unsigned integers or strings), or may contain text.
* **Measurements** including laboratory test results in numerical format. Values may also come with a unit column, which could be text or enum, and may also come with a range.
* **Demographic information** including age, gender, ethnic origin, etc. The format of these columns could be text or numbers.

Columns contain NULLs, which can have meanings other than missing data. Data that come with an index (for example, secondary diagnosis columns) may use a single row and multiple columns (one per index), or use multiple rows, and two columns (one to indicate the index and the second to indicate the value). 

The following sections contain specifications for example synthetic tables. Discrepancies between the types of columns and the semantic content (for example, a nullable column that cannot be null, and behaves as a primary key) is due to the requirement to copy as closely as possible real datasets for testing purposes. Column descriptions clarify the actual content of the column.

### Pharmacy on admission table: `pharmacy_administration`

This table contains medication that patients were taking when they arrived at the hospital. The table is called "administration" because the information is extracted from the discharge summary by the administrative team.

The columns, SQL Server types, and descriptions are given below:

* `subject`, nvarchar(30), nullable: contains a string in the form `bristol_<NUM>`, where `<NUM>` is a positive integer.
* `prescription_order_id`, nvarchar(30), nullable: always NULL in this synthetic data
* `therapeutical_class`, ncharchar(30), nullable: always NULL in this synthetic data
* `medication_name`, nvarchar(4000), nullable: the name of the medication prescribed; one of 979 different values (including "CLOPIDOGREL", "PRASUGREL", "TICAGRELOR", and "WARFARIN SODIUM"), always fully capitalised.
* `administration_date_time`, datetime, nullable: date time column which is always equal to `ADMIT_DTTM`
* `dosage_unit`, nvarchar(80), nullable: medication-specific string indicating the dose units for the prescribed medication.
* `route`, nvarchar(80), nullable: the method of medication administration; one of 29 options, including "Oral" (and "Orally"), "Intravenous", etc. Column does contain NULLs.
* `brc_name`, nvarchar(10), nullable: name of source of test information. Always equal to "bristol". Does not contain NULLs.
* `IP_SPELL_ID`, nvarchar(30), nullable: key linking to the `spell_identifier` in the `episodes` table. Format is `bristol_<NUM>` where `<NUM>` is a positive integer.
* `ADMIT_DTTN`, datetime, nullable: the admission datetime (for the associated spell?)
* `DISCH_DTTN`, datetime, nullable: the discharge datetime (for the associated spell?) 
* `Site of Admin`, nvarchar(12), nullable: always NULL in this synthetic data.
* `Medication Order Type`, varchar(12), not nullable: always equal to "On Admission" in this synthetic data.
* `Medication - Frequency`, nvarchar(80), nullable: how often the medication should be table; expression such as "TWICE a day", "at NIGHT", "daily", etc. (2342 variants in original dataset).
* `Medication - On Admission`, nvarchar(80), nullable: indicates further information about the medication state on admission. Valid values are:
    * NULL
    * "Continued" - medication is left the same on discharge as admission
    * "Changed" - medication changed (often the dose or frequency) on discharge compared to admission
    * "Stopped/Held" - means medication was discontinued at discharge vs. admission
    * "Omitted on admission" - during the spell the patient does not take the medication; this is really independent information from "changed", "stopped/held" or "continued".
    * "Added by Pharmacist Prescriber" - newly prescribed
    * "Added via Pharmacy Enabling Policy" - meaning not known.

#### Aspirin

Aspirin is recorded in the dataset in the following format:
* `medication_name`: "ASPIRIN" or "ASPIRIN [UNLICENSED]"
* `dosage_unit`: May be the following values (most common value "75mg"):
    * NULL
    * A string composed of the following optional items in any order, separated by any separaters (e.g. " ", ";"):
        * A value with a unit, e.g. "75mg". The value is typically 75, but includes 37.5, 40, 75, 80, 85, 225, 300, 600, 900. The unit is often "mg", but includes variants such as "g" (likely not grams), "m", "mcg" (to check). There may or may not be a space between the value and unit.
        * A gastro-resistant type indication: one of "gr", "G/R", "GR", "gastroresistant", "gastro-resistant", "gatsro resistant", "gastro -resistant", "gastro-resisttant" "GASTRO RESISTANT", "GASTRO-RESISTANT", "Gastro-resistant"
        * May include the mark ec (meaning?): "E/C", "ec"
        * An optional tablet/soluble indicator: "dispensible tablets", "disp tabs", "disp", "tablets", "soluble"
    * "Taking OTC"
* `Medication - Frequency`: One of the following (most common values "ONCE a day" and "in the MORNING"):
    * NULL 
    * "Once daily", "OD", "daily", "ONCE a day until review", "ONCE a day for 14 days", "ONCE a day at 6pm", "ONCE a day", "ONCE a day at lunchtime", "ONCE a day at lunch", "ONCE a day in the morning", "at NIGHT", "Every morning", "ONCE in the morning til seen in clinic"
    * "TWICE a day"
    * "TWICE a week"
    * "every 48 hours", "alternate days"
    * "FOUR times a day"

### Blood test results table: `pathology_blood`

This table contains blood test results. Columns, SQL Server types, and descriptions are given below:

* `subject`, nvarchar(30), nullable: contains a string in the form `bristol_<NUM>`, where `<NUM>` is a positive integer.
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

Specific blood tests present in the synthetic table are described in the sections below.

#### Haemoglobin (Hb) Tests

The haemoglobin measurement contains the following information:

* `order_name`: "FULL BLOOD COUNT"
* `test_name`: "Haemoglobin"
* `test_result`: a non-negative integer (i.e. not fractional part)
* `result_*_range`: 120 - 150 for female, 130 - 170 for male (not that gender is not specified in the table)
* `test_result_unit`: "g/L". Note that g/dL is also a common unit for Hb count.

#### Platelet Count

The platelet count measurement contains the following information:

* `order_name`: "FULL BLOOD COUNT"
* `test_name`: "Platelets"
* `test_result`: a non-negative integer (i.e. not fractional part)
* `result_*_range`: 150 - 400, independent of gender
* `test_result_unit`: "10\*9/L" (\* not a typo). This is a volumetric count, 10^9/L

#### Estimated Glomerular Filtration Rate

The eGFR is used as a general indicator of kidney function. The measurement contains the following information:

* `order_name`: "UREACREAT + ELECTROLYTES"
* `test_name`: "eGFR/1.73m2 (CKD-EPI)"
* `test_result`: a non-negative integer <90, or the string ">90"
* `result_*_range`: NULL - NULL
* `test_result_unit`: "mL/min"

## Testing the Patient Structure

The central data structure which represents the interface between the data sources and the higher level users (either data processing in R or python, or graphical presentation of the information) is the `Patient` class. This is a nested structure of many different pieces of information.

There are too many configurations of the structure to test exhaustively. The tests should be informed by the various use cases for `Patient`. Tests should avoid retesting functionality that is already unit tested in lower level structures, or that simply involves writing and then directly reading the fields. Instead, the tests should focusses on interfaces to `Patient` where non-trivial processing is performed on the internal data. 

**TODO list examples that need testing here**
