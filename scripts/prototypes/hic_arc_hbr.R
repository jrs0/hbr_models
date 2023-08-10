##' Prototype calculation of ARC HBR score from HIC dataset

start_time <- Sys.time()

# Set the working directory here
setwd("scripts/prototypes")

library(tidyverse)

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

episodes_id <- dbplyr::in_catalog("HIC_COVID_JS", "dbo", "cv_covid_episodes")
raw_episodes_data <- dplyr::tbl(con, episodes_id) %>%
    select(
        ID, # Key for the diagnosis and procedure tables
        subject, # Patient identifier
        spell_identifier,
        arrival_dt_tm, # Taking hospital arrival time as spell start time
    ) %>%
    rename(
        episode_id = ID,
        spell_id = spell_identifier,
        spell_start_date = arrival_dt_tm,
    ) %>%
    filter(!is.na(subject)) %>%
    filter(spell_start_date > start_date, spell_start_date < end_date) %>%
    collect()

diagnoses_id <- dbplyr::in_catalog("HIC_COVID_JS", "dbo", "cv_covid_episodes_diagnosis")
raw_diagnoses_data <- dplyr::tbl(con, diagnoses_id) %>%
    select(
        ID,
        diagnosis_code_icd,
    ) %>%
    collect() %>%
    transmute(
        episode_id = ID,
        clinical_code = diagnosis_code_icd,
        clinical_code_type = "diagnosis"
    )

procedures_id <- dbplyr::in_catalog("HIC_COVID_JS", "dbo", "cv_covid_episodes_procedures")
raw_procedures_data <- dplyr::tbl(con, procedures_id) %>%
    select(
        ID,
        procedure_code_opcs,
    ) %>%
    collect() %>%
    transmute(
        episode_id = ID,
        clinical_code = procedure_code_opcs,
        clinical_code_type = "procedure"
    )

####### DEFINE ICD-10 and OPCS-4 CODE GROUPS #######

##' Get all the codes in a code group, with the dot removed
##' and converted to all-lowercase, ready for matching with
##' codes in columns
codes_for_matching <- function(codes_file_path, group) {
    get_codes_in_group(codes_file_path, group) %>%
        pull(name) %>%
        str_replace("\\.", "") %>%
        tolower()
}

# Diagnosis groups
bleeding_al_ani <- codes_for_matching(
    "../codes_files/icd10.yaml",
    "bleeding_al_ani"
)
mi_schnier <- codes_for_matching(
    "../codes_files/icd10.yaml",
    "mi_schnier"
)
mi_stemi_schnier <- codes_for_matching(
    "../codes_files/icd10.yaml",
    "mi_stemi_schnier"
)
mi_nstemi_schnier <- codes_for_matching(
    "../codes_files/icd10.yaml",
    "mi_nstemi_schnier"
)

# List of OPCS-4 codes identifying PCI procedures
pci <- codes_for_matching(
    "../codes_files/opcs4.yaml",
    "pci"
)

####### COUNT UP OCCURRENCES OF CODE GROUPS IN EACH SPELL #######

# Collect together all the diagnosis and procedure information
# into a single table in long format, along with the episode id
raw_clinical_codes <- raw_diagnoses_data %>%
    bind_rows(raw_procedures_data)
episode_diagnoses_and_procedures <- raw_episodes_data %>%
    select(episode_id) %>%
    left_join(raw_clinical_codes, by = "episode_id")

# Count up instances of different code groups inside each 
# episode
code_group_counts <- episode_diagnoses_and_procedures %>%
    # Remove the dot from the codes and convert to lower case to compare with the code
    # lists
    mutate(clinical_code = clinical_code %>% str_replace_all("(\\.| )", "") %>% tolower()) %>%
    group_by(episode_id) %>%
    summarise(
        bleeding_al_ani_count = sum(clinical_code %in% bleeding_al_ani &
            clinical_code_type == "diagnosis"),
        mi_schnier_count = sum(clinical_code %in% mi_schnier &
            clinical_code_type == "diagnosis"),
        mi_stemi_schnier_count = sum(clinical_code %in% mi_stemi_schnier &
            clinical_code_type == "diagnosis"),
        mi_nstemi_schnier_count = sum(clinical_code %in% mi_nstemi_schnier &
            clinical_code_type == "diagnosis"),
        pci_count = sum(clinical_code %in% pci &
            clinical_code_type == "procedure"),
    )

####### FIND THE INDEX EVENTS (MI OR PCI) #######

# Index events are identified by whether the first
# episode of the spell is a MI or a PCI

index_episodes <- code_group_counts %>%
    # Join the episode data to add the episode and spell start
    # date to the code count information for each episode
    left_join(raw_episodes_data, by = "episode_id")

