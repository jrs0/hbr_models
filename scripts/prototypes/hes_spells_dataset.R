##' Download and process the HES spells database into a dataset
##'
##' !!! Note: this script is not yet working
##'
##' In the dataset, each row is a spell, with diagnoses and procedures
##' summarised (in some way) from the underlying episodes. This script
##' uses the data to produce a dataframe with the following columns:
##'
##' Any columns beginning with pred_ are predictors. Some of the predictors
##' are derived from the index event, and these begin pred_idx_. Columns
##' containing outcomes begin outcome_. Columns containing index information
##' that is not to be used as a predictor begins idx_.
##'
##' Index event information:
##'
##' An index event is defined as having a PCI procedure or an MI
##' diagnosis code (mi_schnier, see below).
##'
##' - idx_date: the date of the index event
##' - pred_idx_age: the patient age at the index event
##' - pred_idx_gender: the patient gender at the index event
##' - pred_idx_pci_performed: was a PCI procedure performed at the index?
##' - pred_idx_mi: did the index include an MI?
##' - pred_idx_stemi: did the index include an MI that was STEMI?
##' - pred_idx_nstemi: did the index include an MI that was NSTEMI?
##'
##' Prior diagnoses and procedures:
##'
##' - pred_<code_group>_count_before: how many ICD-10 or OPCS-4 codes
##'      occurred in the window [12 months before to 1 month before]
##'      the index event. The 1 month limit simulates lack of
##'      availability for one month due to the coding process
##'
##' Outcomes:
##'
##' - outcome_time_<name>: the time to the outcome <name>, or right
##'      censored using the end date range of the database
##' - outcome_status_<name>: 1 if the outcome event was observed to
##'      occur, 0 if right-censored
##' - outcome_occurred_<name>: 1 if the event was observed to occur in the
##'      12 months following the index event
##'
##' The following outcomes (<name>) are included:
##'
##' - bleeding_al_ani: a group of ICD-10 bleeding codes based on a
##'      set reported to have 88% PPV for identifying major bleeding in
##'      2015 Al-Ani et al., Identifying venous thromboembolism and major
##'      bleeding in emergency room discharge using administrative data
##' - mi_schnier: a group of ICD-10 myocardial infarction codes based
##'      on a set defined in 2015 Al-Ani et al., Identifying venous
##'      thromboembolism and major bleeding in emergency room discharges
##'      using administrative data, estimated to have a PPV >75% for MI
##'      as defined in that document.
##'
##' The script should be run from this folder (set the working directory
##' to scripts/prototypes). The resulting dataset is saved in the folder
##' scripts/prototypes/datasets as an rds file "hes_spells_dataset.rds"

start_time <- Sys.time()

# Set the working directory here
setwd("scripts/prototypes")

library(tidyverse)
source("preprocessing.R")
source("save_datasets.R")

# Either load rhbr using rextendr::document() (from the rhbr/ directory)
# or install rhbr and use library(rhbr). Pick one of the options from
# below
# library(rhbr)
rextendr::document(pkg = "../../rhbr")

con <- DBI::dbConnect(odbc::odbc(), "xsw", bigint = "character")
id <- dbplyr::in_catalog("abi", "dbo", "vw_apc_sem_spell_001")

####### GET THE RAW DATA #######

# Date range for the data. This is necessary for computing right censoring
# for the survival data. To be valid, make sure that the database contains data
# for the full date range given here -- the end date is used as the follow up
# time for right censoring.
start_date <- lubridate::ymd_hms("2020-01-01 00:00:00")
# Go careful with the end date -- data must be present in the
# dataset up the the end date (for right censoring). Should really
# compute right censor date from last seen date in the data
end_date <- lubridate::ymd_hms("2022-01-01 00:00:00")

# Raw spell data from the database. This is just a spell table, so
# episode information has been summarised into a single row.
raw_data <- dplyr::tbl(con, id) %>%
    select(
        PBRspellID,
        AIMTC_Pseudo_NHS,
        AIMTC_Age,
        AIMTC_ProviderSpell_Start_Date,
        Sex,
        matches("^(Primary)?Procedure") & !contains("Date") & !contains("Scheme"),
        matches("Diagnosis") & !contains("Date") & !contains("Scheme")
    ) %>%
    rename(
        spell_id = PBRspellID,
        patient = AIMTC_Pseudo_NHS,
        age = AIMTC_Age,
        gender = Sex,
        spell_start_date = AIMTC_ProviderSpell_Start_Date
    ) %>%
    filter(!is.na(patient)) %>%
    filter(spell_start_date > start_date, spell_start_date < end_date) %>%
    collect()

# Found that the database contains duplicate spell IDs, and rows
# where the spell ID is the empty string or whitespace. Remove all these rows
raw_spell_data <- raw_data %>%
    group_by(spell_id) %>%
    filter(
        !grepl("^\\s*$", spell_id), # No whitespace IDs
        n() == 1 # IDs must be unique
    ) %>%
    ungroup()

## checked up to here ------------------------------------------------------------

# Find the last date seen in the dataset to use as an approximation for
# the right-censor date for the purpose of survival analysis
right_censor_date <- raw_spell_data %>%
    pull(spell_start_date) %>%
    max()

# Also helpful to know the earliest date in the dataset. This is important
# for whether it is possible to know predictors a certain time in advance.
left_censor_date <- raw_spell_data %>%
    pull(spell_start_date) %>%
    min()

# For joining NHS number by spell id later on
patients <- raw_spell_data %>%
    select(spell_id, patient)

# For joining spell information by spell id later
age_and_gender <- raw_data %>%
    select(spell_id, age, gender) %>%
    mutate(gender = case_when(
        gender == 0 ~ "unknown",
        gender == 1 ~ "male",
        gender == 2 ~ "female",
        gender == 9 ~ NA_character_,
    ))

####### DEFINE ICD-10 and OPCS-4 CODE GROUPS #######


####### COUNT UP OCCURRENCES OF CODE GROUPS IN EACH SPELL #######

# The goal is to merge all of the diagnoses into a single column.
# values_drop_na is used to prevent diagnosis columns containing NULL
# becoming rows. There aren't too many of these, because most are the
# empty string instead. These are filtered out next. Once all the codes
# are in one column, the result is summarised by counting up how many
# of the codes fall into each clinical code group (each count is added
# as a new column)
#
# Code crashes in this block due to out of memory

# Collect together all the diagnosis and procedure information
# into a single table in long format, along with the episode id
spell_diagnoses_and_procedures <- raw_spell_data %>%
    pivot_longer(
        (matches("Diagnosis") & !contains("Date") & !contains("Scheme")) |
            (matches("^(Primary)?Procedure") & !contains("Date") & !contains("Scheme")),
        names_to = "clinical_code_type", values_to = "clinical_code",
        values_drop_na = TRUE
    ) %>%
    filter(clinical_code != "") %>%
    # Now that all the ICD-10 and OPCS-4 codes are in one long column, replace the
    # original diagnosis and procedure column names with a marker indicating diagnosis
    # or procedure
    mutate(clinical_code_type = if_else(
        str_detect(clinical_code_type, "iagnosis"),
        "diagnosis",
        "procedure"
    )) %>%
    select(
        spell_id,
        clinical_code,
        clinical_code_type
    )

# Just extract the MI diagnoses for plotting
diagnoses <- spell_diagnoses_and_procedures %>%
    mutate(clinical_code = clinical_code %>% str_replace_all("(\\.| )", "") %>% tolower()) %>%
    filter(
        clinical_code_type == "diagnosis",
        (clinical_code %in% acs_bezin) |
            (clinical_code %in% mi_stemi_schnier) |
            (clinical_code %in% mi_nstemi_schnier)
    ) %>%
    transmute(
        clinical_code,
        group = case_when(
            (clinical_code %in% mi_stemi_schnier) ~ "stemi",
            (clinical_code %in% mi_nstemi_schnier) ~ "nstemi",
            (clinical_code %in% acs_bezin) ~ "other_mi",
        )
    )

# Plot the distribution of different MI codes. It is seen that
# I25.2 (Old myocardial infarction) dominates the other MI group
# (i.e. MI that is not in the STEMI or NSTEMI groups). This code
# must be excluded, because it is not an acute coronary syndrome.
library(ggplot2)
diagnoses %>%
    ggplot(aes(x = clinical_code, fill = group)) +
    geom_bar(stat = "count") +
    scale_y_log10() +
    labs(
        title = "Distribution of ICD-10 codes within the MI (Schnier) group",
        x = "ICD-10 code",
        y = "Total count (Note logarithmic scale)"
    )

# Count up instances of different code groups inside each
# episode
code_group_counts <- spell_diagnoses_and_procedures %>%
    # Remove the dot from the codes and convert to lower case to compare with the code
    # lists
    mutate(clinical_code = clinical_code %>% str_replace_all("(\\.| )", "") %>% tolower()) %>%
    # Group into spells (which also groups by nhs_number, assuming spell_id is unique even
    # between patients), and count the number of diagnosis and procedure codes in each group
    group_by(spell_id) %>%
    summarise(
        bleeding_al_ani_count = sum(clinical_code %in% bleeding_al_ani &
            clinical_code_type == "diagnosis"),
        mi_schnier_count = sum(clinical_code %in% mi_schnier &
            clinical_code_type == "diagnosis"),
        mi_stemi_schnier_count = sum(clinical_code %in% mi_stemi_schnier &
            clinical_code_type == "diagnosis"),
        mi_nstemi_schnier_count = sum(clinical_code %in% mi_nstemi_schnier &
            clinical_code_type == "diagnosis"),
        ihd_bezin_count = sum(clinical_code %in% ihd_bezin &
            clinical_code_type == "diagnosis"),
        acs_bezin_count = sum(clinical_code %in% acs_bezin &
            clinical_code_type == "diagnosis"),
        pci_count = sum(clinical_code %in% pci &
            clinical_code_type == "procedure"),
    )

####### GET THE INDEX EVENTS (ACS OR PCI SPELL) #######

# Note that the spell start date is used as the index date.

# Get the spell id of index spells. The index spells are defined as the
# as the ACS group defined by Bezin et al. 
idx_spells <- code_group_counts %>%
    filter(acs_bezin_count > 0 | pci_count > 0) %>%
    transmute(
        idx_spell_id = spell_id
    )

# Derive data about the index spell from the counts and spell data
idx_spell_info <- idx_spells %>%
    left_join(code_group_counts, by = c("idx_spell_id" = "spell_id")) %>%
    # Record whether the index event is PCI or conservatively managed (ACS).
    # Record STEMI and NSTEMI as separate columns to account for possibility
    # of neither (i.e. no ACS).
    transmute(
        idx_spell_id,
        pci_performed = (pci_count > 0), # If false, conservatively managed
        stemi = (mi_stemi_schnier_count > 0),
        nstemi = (mi_nstemi_schnier_count > 0),
        acs = (acs_bezin_count > 0),
    )

####### COMPUTE COUNT OF PREVIOUS DIAGNOSES AND PROCEDURES #######

# The first step is knowing the time of the index events, which is
# obtained by first getting the dates/times of all spells
spell_dates_by_patient <- raw_spell_data %>%
    select(spell_id, patient, spell_start_date)

# Do the same for the index spells
idx_dates_by_patient <- idx_spells %>%
    left_join(raw_spell_data, by = c("idx_spell_id" = "spell_id")) %>%
    transmute(
        idx_spell_id,
        patient,
        idx_date = spell_start_date
    )

# Join all the spells' dates back on by patient to get each patient's
# index events paired up with all their other spells.
# Note that this table has negative times for spells before the index.
# This table also contains the index event itself as a row with 0 time.
time_from_index_to_spell <- idx_dates_by_patient %>%
    # Expect many-to-many because the same patient could have
    # multiple index events.
    left_join(spell_dates_by_patient,
        by = "patient", relationship = "many-to-many"
    ) %>%
    # Calculate the time from index to episode
    transmute(
        idx_spell_id,
        spell_id,
        index_to_spell_time = spell_start_date - idx_date
    )

# This table contains the total number of each diagnosis and procedure
# group in a period before the index event. This could be the previous
# 12 months, excluding the month before the index event (to account for
# lack of coding data in that period)
max_period_before <- lubridate::dyears(1) # Limit count to previous 12 months
min_period_before <- lubridate::dmonths(1) # Exclude month before index (not coded yet)

# These are the spells whose clinical code counts should contribute
# to predictors.
spells_in_window_before_index <- time_from_index_to_spell %>%
    filter(
        index_to_spell_time < -min_period_before,
        -max_period_before < index_to_spell_time,
    ) %>%
    select(idx_spell_id, spell_id)

# Compute the total count for each index event that has a spell
# in the valid window before the index. Note that this excludes
# index events with zero spells before the index.
nonzero_code_counts_before <- spells_in_window_before_index %>%
    left_join(code_group_counts, by = "spell_id") %>%
    group_by(idx_spell_id) %>%
    summarize(across(matches("_count"), sum)) %>%
    # Append "_before" to all count columns
    rename_with(~ paste0(., "_before"), matches("count"))

# Join back all the index events that do not have any episodes
# beforehand,
code_counts_before <- idx_spells %>%
    full_join(nonzero_code_counts_before, by = "idx_spell_id") %>%
    # In the full join, any index events not in the nonzero counts
    # table show up as NAs in the result. Replace these with zero
    # to indicate none of the code groups were present as predictors
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

# These are the subsequent spells after the index, with
# the index row also retained.
spells_after <- time_from_index_to_spell %>%
    filter(
        # Exclude a short window after the index
        (index_to_spell_time > min_period_after)
        # Retain the index events in the table
        | (spell_id == idx_spell_id),
    ) %>%
    left_join(code_group_counts, by = "spell_id") %>%
    left_join(idx_dates_by_patient, by = "idx_spell_id")

# Get the list of outcomes as a character vector
outcome_list <- c("bleeding_al_ani", "mi_schnier")

# Compute the outcome columns: outcome status (whether it
# occurred or not), time-to-outcome (or right-censored time),
# and an outcome occurred flag derived from the previous two
# columns, which is NA if it cannot be determined whether the
# outcome occurred or not.
idx_with_subsequent_outcomes <- spells_after %>%
    add_outcome_columns(
        spell_id,
        idx_spell_id,
        index_to_spell_time,
        idx_date,
        outcome_list,
        right_censor_date,
        follow_up
    )

# Finally, join all the index data to form the dataset
hes_spells_dataset <- idx_spell_info %>%
    left_join(idx_dates_by_patient, by = "idx_spell_id") %>%
    left_join(idx_with_subsequent_outcomes, by = "idx_spell_id") %>%
    left_join(code_counts_before, by = "idx_spell_id") %>%
    left_join(age_and_gender, by = c("idx_spell_id" = "spell_id")) %>%
    transmute(
        # Index information
        idx_date,
        pred_idx_age = age,
        pred_idx_gender = gender,
        pred_idx_pci_performed = pci_performed,
        pred_idx_stemi = stemi,
        pred_idx_nstemi = nstemi,
        pred_idx_acs = acs,
        # Counts of previous codes
        pred_bleeding_al_ani_count_before = bleeding_al_ani_count_before,
        pred_mi_schnier_count_before = mi_schnier_count_before,
        pred_mi_stemi_schnier_count_before = mi_stemi_schnier_count_before,
        pred_mi_nstemi_schnier_count_before = mi_nstemi_schnier_count_before,
        pred_pci_count_before = pci_count_before,
        # Outcomes
        outcome_time_bleeding_al_ani = bleeding_al_ani_time,
        outcome_status_bleeding_al_ani = bleeding_al_ani_status,
        outcome_occurred_bleeding_al_ani = bleeding_al_ani_occurred,
        outcome_time_mi_schnier = mi_schnier_time,
        outcome_status_mi_schnier = mi_schnier_status,
        outcome_occurred_mi_schnier = mi_schnier_occurred,
    )

save_dataset(hes_spells_dataset, "hes_spells_dataset")

end_time <- Sys.time()

# Calculate the script running time
end_time - start_time
