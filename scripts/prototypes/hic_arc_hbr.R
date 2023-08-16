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

####### GET THE RAW DATA FOR DIAGNOSES AND PROCEDURES #######

# In this dataset, diagnosis and precedure information is held across
# three tables: one for episodes (with a primary key), and two others
# containing the diagnoses and procedures in long format.

con <- DBI::dbConnect(odbc::odbc(), "hic", bigint = "character")

raw_episodes_data <- get_episodes_hic(con, start_date, end_date)

# Mapping from episode_id to patient. Required later for joining
# episodes together from different tables by patient.
patients <- raw_episodes_data %>%
    select(episode_id, patient_id)

# Get a long list of clinical codes (ICD-10 and OPCS-4) for each episode
# (there are multiple codes per episode)
raw_diagnoses_and_procedures <- get_diagnoses_and_procedures_hic(con)

# Get the code groups that are in the codes files
code_groups <- get_code_groups("../codes_files/icd10.yaml", "../codes_files/opcs4.yaml")

# Reduce 
code_group_counts <- raw_diagnoses_and_procedures %>%
    count_code_groups_by_record(episode_id, code_groups)

    count_code_groups_by_record(raw_diagnoses_and_procedures, episode_id, code_groups)