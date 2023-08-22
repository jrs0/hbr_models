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

all_episodes <- raw_episodes_data %>%
    select(episode_id)

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

####### DEMOGRAPHICS #######

raw_demographics <- get_demographics(con)

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
# - 10*9/L (meaning 1e9 platelets per litre) for Platelets
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
        sample_collected
    )

####### COMPUTE ARC-HBR CRITERIA IN EACH EPISODE #######

# Anaemia
# - For men and women, major (1) if Hb < 110 g/L
# - For women, minor (0.5) if Hb < 119 g/L
# - For men, minor (0.5) if Hb < 129 g/L
# - 0 otherwise
arc_hbr_anaemia <- blood_tests %>%
    # Need patient gender from demographics
    left_join(raw_episodes_data, by = "episode_id") %>%
    left_join(raw_demographics, by = "patient_id") %>%
    # Calculate the ARC HBR criterion for each blood test
    mutate(arc_hbr_anaemia = case_when(
        (test == "Haemoglobin") & (result < 110) ~ 1,
        (test == "Haemoglobin") & (gender == "female") & (result < 119) ~ 0.5,
        (test == "Haemoglobin") & (gender == "male") & (result < 129) ~ 0.5,
        TRUE ~ 0,
    )) %>%
    # Reduce by taking the maximum score over all the blood tests for
    # each episode
    group_by(episode_id) %>%
    summarise(arc_hbr_anaemia = max(arc_hbr_anaemia)) %>%
    # Join on all the episodes that did not have any blood test
    # results (will right join as NA) and replace the
    # NA with zero to indicate no HBR criterion.
    right_join(all_episodes, by = "episode_id") %>%
    mutate(arc_hbr_anaemia = replace_na(arc_hbr_anaemia, 0))

# Thrombocytopenia (low platelet count)
# - Baseline platelet count < 100e9/L
#
# The baseline is the count before the PCI. In order to
# approximate this, we are picking the first platelet
# measurement of each episode, on the assumption that
# this is often done for ACS prior to PCI. This assumption
# should be checked by comparing the sample collected
# time to the PCI time, but this is not possible if the
# PCI occurred as a code in the episode (because individual)
# codes are not timestamped within an episode. It may
# be possible when the PCI occurs in a different episode
# (as it sometimes does), but that case is not covered
# here anyway. This is a suitable approximation for
# prototyping purposes.
#
# "The reported prevalence of baseline thrombocytopenia
# in patients undergoing PCI is ~2.5% in the United States
# and 1.5% in Japan" (Urban et al., 2019), so expect mean
# of arc_hbr_tcp column approx. 0.015 to 0.025.
#
arc_hbr_tcp <- blood_tests %>%
    filter(test == "Platelets") %>%
    # Reduce by taking the _first_ platelet count reading
    # (approximation to baseline) within in episode
    arrange(episode_id, sample_collected) %>%
    group_by(episode_id) %>%
    summarise(first_platelet_count = first(result)) %>%
    # Calculate the ARC HBR criterion for each episode
    mutate(arc_hbr_tcp = case_when(
        (first_platelet_count < 100) ~ 1,
        TRUE ~ 0,
    )) %>%
    select(
        episode_id,
        arc_hbr_tcp
    ) %>%
    # Join on all the episodes that did not have any blood test
    # results (will right join as NA) and replace the
    # NA with zero to indicate no HBR criterion.
    right_join(all_episodes, by = "episode_id") %>%
    mutate(arc_hbr_tcp = replace_na(arc_hbr_tcp, 0))
