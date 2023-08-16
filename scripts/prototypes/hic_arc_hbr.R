##' Prototype calculation of ARC HBR score from HIC dataset

start_time <- Sys.time()

# Set the working directory here
setwd("scripts/prototypes")

library(tidyverse)
source("preprocessing.R")
source("save_datasets.R")
source("hic.R")
source("code_group_counts.R")

# Either load rhic using rextendr::document() (from the rhic/ directory)
# or install rhic and use library(rhic). Pick one of the options from
# below
# library(rhic)
rextendr::document(pkg = "../../rhic")

####### DATE RANGE FOR DATA COLLECTION #######

# Date range for the data. This is necessary for computing right censoring
# for the survival data. To be valid, make sure that the database contains data
# for the full date range given here -- the end date is used as the follow up
# time for right censoring.
start_date <- lubridate::ymd_hms("2020-01-01 00:00:00")
# Go careful with the end date -- data must be present in the
# dataset up the the end date (for right censoring). Should really
# compute right censor date from last seen date in the data
end_date <- lubridate::ymd_hms("2023-01-01 00:00:00")

####### DATABASE CONNECTION

con <- DBI::dbConnect(odbc::odbc(), "hic", bigint = "character")

####### GET THE RAW DATA FOR DIAGNOSES AND PROCEDURES #######

# In this dataset, diagnosis and precedure information is held across
# three tables: one for episodes (with a primary key), and two others
# containing the diagnoses and procedures in long format.

raw_episodes_data <- get_episodes_hic(con, start_date, end_date)

# Get a long list of clinical codes (ICD-10 and OPCS-4) for each episode
# (there are multiple codes per episode)
raw_diagnoses_and_procedures <- get_diagnoses_and_procedures_hic(con)

# Mapping from episode_id to patient. Required later for joining
# episodes together from different tables by patient.
patients <- raw_episodes_data %>%
    select(episode_id, patient_id)

####### COUNT THE OCCURANCES OF CODES IN EACH GROUP #######

# Get the code groups that are in the codes files
code_groups <- get_code_groups("../codes_files/icd10.yaml", "../codes_files/opcs4.yaml")

# Reduce the diagnosis and procedures to a total count in each group by
# episode id
code_group_counts <- raw_diagnoses_and_procedures %>%
    count_code_groups_by_record(episode_id, code_groups)

####### BLOOD TEST RESULTS #######

# Get the full set of blood test results.
raw_blood_tests <- get_blood_tests_hic(con, start_date, end_date) %>%
    # Only the families "FULL BLOOD COUNT" and "UREACREAT + ELECTROLYTES" are
    # of interest (includes Haemoglobin, platelets and eGFR)
    filter(family == "FULL BLOOD COUNT" | family == "UREACREAT + ELECTROLYTES") %>%
    # Filter specifically to just get Hb, Plt and eGFR, and rename the values
    filter(test == "Haemoglobin" | test == "Platelets" | test == "eGFR/1.73m2 (CKD-EPI)") %>%
    # The results column contains the word "Pending" if the result is
    # not available. Filter these out.
    filter(result != "Pending") %>%
    transmute(
        patient_id,
        test = str_replace(test, "eGFR/1\\.73m2 \\(CKD-EPI\\)", "eGFR"),
        result,
        unit,
        sample_collected
    )

# Expect exactly three units:
# - g/L for Hb
# - 10*9/L (meaning count per 1e9) for Platelets
# - mL/min for eGFR
units <- raw_blood_tests %>%
    distinct(unit) %>%
    pull()
stopifnot(identical(units, c("g/L", "10*9/L", "mL/min")))

# If this check passes, can drop the units column. In addition,
# the results are all numeric, apart from the string ">90" in the
# eGFR column. This will be replaced with 90.
blood_tests_numeric_results <- raw_blood_tests %>%
    select(-unit) %>%
    mutate(result = str_replace(result, ">", "")) %>%
    mutate(result = as.numeric(result))

# Want to associate each blood test with the episode in which it
# occurred.
blood_tests <- blood_tests_numeric_results %>%
    # Expecting many-to-many because, for each patient, we want all episodes to be
    # joined to all their blood tests (the next step will remove the tests not
    # associated with a particular episode).
    full_join(raw_episodes_data, by = "patient_id", relationship = "many-to-many") %>%
    # Only keep (blood test) rows where the sample was collected inside the start
    # and end time of the episode.
    filter(
        sample_collected >= episode_start_date,
        sample_collected < episode_end_date,
    ) %>%
    transmute(
        episode_id,
        test,
        result,
    )
