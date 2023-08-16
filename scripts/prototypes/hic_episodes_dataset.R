##' Prototype calculation of ARC HBR score from HIC dataset

start_time <- Sys.time()

# Set the working directory here
setwd("scripts/prototypes")

library(tidyverse)
source("preprocessing.R")
source("save_datasets.R")

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
        episode_identifier, # Key for the diagnosis and procedure tables
        subject, # Patient identifier
        spell_identifier,
        # Taking hospital arrival time as spell start time for the purpose
        # of calculating time-to-subsequent events
        arrival_dt_tm,
        episode_start_time,
    ) %>%
    rename(
        episode_id = episode_identifier,
        patient = subject,
        spell_id = spell_identifier,
        spell_start_date = arrival_dt_tm,
        episode_start_date = episode_start_time,
    ) %>%
    filter(!is.na(patient)) %>%
    # filter(spell_start_date > start_date, spell_start_date < end_date) %>%
    collect()

# Find the last date seen in the dataset to use as an approximation for
# the right-censor date for the purpose of survival analysis
right_censor_date <- raw_episodes_data %>%
    pull(episode_start_date) %>%
    max()

# Also helpful to know the earliest date in the dataset. This is important
# for whether it is possible to know predictors a certain time in advance.
left_censor_date <- raw_episodes_data %>%
    pull(episode_start_date) %>%
    min()

# Mapping from episode_id to patient. Required later for joining
# episodes together from different tables by patient.
patients <- raw_episodes_data %>%
    select(episode_id, patient)

diagnoses_id <- dbplyr::in_catalog("HIC_COVID_JS", "dbo", "cv_covid_episodes_diagnosis")
raw_diagnoses_data <- dplyr::tbl(con, diagnoses_id) %>%
    select(
        episode_identifier,
        diagnosis_code_icd,
    ) %>%
    collect() %>%
    transmute(
        episode_id = episode_identifier,
        clinical_code = diagnosis_code_icd,
        clinical_code_type = "diagnosis"
    )

procedures_id <- dbplyr::in_catalog("HIC_COVID_JS", "dbo", "cv_covid_episodes_procedures")
raw_procedures_data <- dplyr::tbl(con, procedures_id) %>%
    select(
        episode_identifier,
        procedure_code_opcs,
    ) %>%
    collect() %>%
    transmute(
        episode_id = episode_identifier,
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

# This is nonsense:
# episode_diagnoses_and_procedures <- raw_episodes_data %>%
#     select(episode_id) %>%
#     left_join(raw_clinical_codes, by = "episode_id")

# Count up instances of different code groups inside each
# episode
code_group_counts <- raw_clinical_codes %>%
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

# This table contains the list of index episodes
idx_episodes <- code_group_counts %>%
    # Join the episode data to add the episode and spell start
    # date to the code count information for each episode
    left_join(raw_episodes_data, by = "episode_id") %>%
    # Pick only the first episode of each spell
    arrange(episode_start_date) %>%
    group_by(spell_id) %>%
    slice_head(n = 1) %>%
    ungroup() %>%
    filter(mi_schnier_count > 0 | pci_count > 0) %>%
    transmute(
        idx_episode_id = episode_id,
        idx_spell_id = spell_id
    )

# Derive data about the index episode. Note: above, we are only including
# index event according to the first episode, which means we are already
# missing cases where an MI is present in the first episode but a PCI is
# performed in a subsequent episode -- there is no point trying to correct
# for it here. That is for a future version of the script.
idx_episode_info <- idx_episodes %>%
    left_join(code_group_counts, by = c("idx_episode_id" = "episode_id")) %>%
    # Record whether the index event is PCI or conservatively managed (ACS).
    # Record STEMI and NSTEMI as separate columns to account for possibility
    # of neither (i.e. no ACS).
    transmute(
        idx_episode_id,
        pci_performed = (pci_count > 0), # If false, conservatively managed
        stemi = (mi_stemi_schnier_count > 0),
        nstemi = (mi_nstemi_schnier_count > 0),
        mi = (mi_schnier_count > 0)
    )

####### COMPUTE COUNT OF PREVIOUS DIAGNOSES AND PROCEDURES #######

# The first step is knowing the time of the index events, which is
# obtained by first getting the dates/times of all episodes
episode_dates_by_patient <- raw_episodes_data %>%
    select(episode_id, patient, episode_start_date)

# Do the same for the index episodes
idx_dates_by_patient <- idx_episodes %>%
    left_join(raw_episodes_data, by = c("idx_episode_id" = "episode_id")) %>%
    transmute(
        idx_episode_id,
        patient,
        # The spell start date is being used as the index date for the
        # purpose of this script.
        idx_date = spell_start_date
    )

# Join all the episodes' dates back on by patient to get each patient's
# index events paired up with all their other episodes.
# Note that this table has negative times for episodes before the index.
# This table also contains the index event itself as a row with 0 time.
time_from_index_to_episode <- idx_dates_by_patient %>%
    # Expect many-to-many because the same patient could have
    # multiple index events.
    left_join(episode_dates_by_patient,
        by = "patient", relationship = "many-to-many"
    ) %>%
    # Calculate the time from index to episode
    transmute(
        idx_episode_id,
        episode_id,
        index_to_episode_time = episode_start_date - idx_date
    )


# This table contains the total number of each diagnosis and procedure
# group in a period before the index event. This could be the previous
# 12 months, excluding the month before the index event (to account for
# lack of coding data in that period)
max_period_before <- lubridate::dyears(1) # Limit count to previous 12 months
min_period_before <- lubridate::dmonths(1) # Exclude month before index (not coded yet)

# These are the episodes whose clinical code counts should contribute
# to predictors.
episodes_in_window_before_index <- time_from_index_to_episode %>%
    filter(
        index_to_episode_time < -min_period_before,
        -max_period_before < index_to_episode_time,
    ) %>%
    select(idx_episode_id, episode_id)

# Compute the total count for each index event that has an episode
# in the valid window before the index. Note that this excludes
# index events with zero episodes before the index.
nonzero_code_counts_before <- episodes_in_window_before_index %>%
    left_join(code_group_counts, by = "episode_id") %>%
    # Don't need the episode_id any more, just need the index
    # episode id to group-by for the summarise. NOTE -- this
    # might not be needed?
    select(-episode_id) %>%
    group_by(idx_episode_id) %>%
    summarize(across(matches("_count"), sum)) %>%
    # Append "_before" to all count columns
    rename_with(~ paste0(., "_before"), matches("count"))

# Join back all the index events that do not have any episodes
# beforehand,
code_counts_before <- idx_episodes %>%
    full_join(nonzero_code_counts_before, by = "idx_episode_id") %>%
    # In the full join, any index events not in the nonzero counts
    # table show up as NAs in the result. Replace these with zero
    # to indicate non of the code groups were present as predictors
    mutate(across(matches("count"), ~ replace_na(., 0)))

####### COMPUTE TIME TO FIRST BLEED AND FIRST MI #######

# This table contains the total number of each diagnosis and procedure
# group in a period after the index event. A fixed window immediately
# after the index event is excluded, to filter out peri-procedural
# outcomes or outcomes that occur in the index event itself. A follow-up
# date is defined that becomes the "outcome_occurred" column in the 
# dataset, for classification models.
follow_up <- lubridate::dyears(1) # Limit "occurred" column to 12 months
min_period_after <- lubridate::dhours(72) # Exclude the subsequent 72 hours after index

# These are the subsequent episodes after the index, with
# the index row also retained.
episodes_after <- time_from_index_to_episode %>%
    filter(
        # Exclude a short window after the index
        (index_to_episode_time > min_period_after)
        # Retain the index events in the table
        | (episode_id == idx_episode_id),
    ) %>%
    left_join(code_group_counts, by = "episode_id") %>%
    left_join(idx_dates_by_patient, by = "idx_episode_id")

# Get the list of outcomes as a character vector
outcome_list <- c("bleeding_al_ani", "mi_schnier")

# Compute the outcome columns: outcome status (whether it
# occurred or not), time-to-outcome (or right-censored time),
# and an outcome occurred flag derived from the previous two
# columns, which is NA if it cannot be determined whether the
# outcome occurred or not.
idx_with_subsequent_outcomes <- episodes_after %>%
    add_outcome_columns(
        episode_id,
        idx_episode_id,
        index_to_episode_time,
        idx_date,
        outcome_list,
        right_censor_date,
        follow_up
    )

hic_episodes_dataset <- idx_episode_info %>%
    left_join(idx_dates_by_patient, by = "idx_episode_id") %>%
    left_join(idx_with_subsequent_outcomes, by = "idx_episode_id") %>%
    left_join(code_counts_before, by = "idx_episode_id") %>%
    transmute(
        # Index information
        idx_date,
        #idx_age = age,
        #idx_gender = gender,
        idx_pci_performed = pci_performed,
        idx_mi = mi,
        idx_stemi = stemi,
        idx_nstemi = nstemi,
        # Counts of previous codes
        bleeding_al_ani_count_before,
        mi_schnier_count_before,
        mi_stemi_schnier_count_before,
        mi_nstemi_schnier_count_before,
        pci_count_before,
        # Outcomes
        outcome_time_bleeding_al_ani = bleeding_al_ani_time,
        outcome_status_bleeding_al_ani = bleeding_al_ani_status,
        outcome_occurred_bleeding_al_ani = bleeding_al_ani_occurred,
        outcome_time_mi_schnier = mi_schnier_time,
        outcome_status_mi_schnier = mi_schnier_status,
        outcome_occurred_mi_schnier = mi_schnier_occurred,
    )

save_dataset(hic_episodes_dataset, "hic_episodes_dataset")

end_time <- Sys.time()

# Calculate the script running time
end_time - start_time