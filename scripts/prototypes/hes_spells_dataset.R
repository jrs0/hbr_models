##' Download and process the HES spells database into a dataset
##'
##' !!! Note: this script is not yet working
##'
##' In the dataset, each row is a spell, with diagnoses and procedures
##' summarised (in some way) from the underlying episodes. This script
##' uses the data to produce a dataframe with the following columns:
##'
##' Index event information:
##'
##' An index event is defined as having a PCI procedure or an MI
##' diagnosis code (mi_schnier, see below).
##'
##' - idx_date: the date of the index event
##' - idx_age: the patient age at the index event
##' - idx_gender: the patient gender at the index event
##' - idx_pci_performed: was a PCI procedure was performed at the index?
##' - idx_mi: did the index include an MI?
##' - idx_stemi: did the index include an MI that was STEMI?
##' - idx_nstemi: did the index include an MI that was NSTEMI?
##'
##' Prior diagnoses and procedures:
##'
##' - <code_group>_count_before: how many ICD-10 or OPCS-4 codes
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
##' - outcome_12m_<name>: 1 if the event was observed to occur in the
##'      12 montsh following the index event
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

# Either load rhic using rextendr::document() (from the rhic/ directory)
# or install rhic and use library(rhic). Pick one of the options from
# below
# library(rhic)
rextendr::document(pkg = "../../rhic")

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
end_date <- lubridate::ymd_hms("2023-01-01 00:00:00")

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
        nhs_number = AIMTC_Pseudo_NHS,
        age = AIMTC_Age,
        gender = Sex,
        spell_start_date = AIMTC_ProviderSpell_Start_Date
    ) %>%
    filter(!is.na(nhs_number)) %>%
    filter(spell_start_date > start_date, spell_start_date < end_date) %>%
    collect()

# For joining NHS number by spell id later on
nhs_numbers <- raw_data %>%
    select(spell_id, nhs_number)

# For joining spell information by spell id later
spell_data <- raw_data %>%
    select(spell_id, age, gender, spell_start_date) %>%
    mutate(gender = case_when(
        gender == 0 ~ "unknown",
        gender == 1 ~ "male",
        gender == 2 ~ "female",
        gender == 9 ~ NA_character_,
    ))

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

# The goal is to merge all of the diagnoses into a single column.
# values_drop_na is used to prevent diagnosis columns containing NULL
# becoming rows. There aren't too many of these, because most are the
# empty string instead. These are filtered out next. Once all the codes
# are in one column, the result is summarised by counting up how many
# of the codes fall into each clinical code group (each count is added
# as a new column)
#
# Code crashes in this block due to out of memory
code_group_counts <- raw_data %>%
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
        pci_count = sum(clinical_code %in% pci &
            clinical_code_type == "procedure"),
    )

####### GET THE INDEX EVENTS (ACS OR PCI SPELL) #######

# Note that the spell start date is used as the index date.

# Get the spell id of index spells
index_spells <- code_group_counts %>%
    filter(mi_schnier_count > 0 | pci_count > 0) %>%
    select(spell_id)

# Derive data about the index spell from the counts and spell data
index_spell_info <- index_spells %>%
    left_join(code_group_counts, by = "spell_id") %>%
    # Record whether the index event is PCI or conservatively managed (ACS).
    # Record STEMI and NSTEMI as separate columns to account for possibility
    # of neither (i.e. no ACS).
    transmute(
        spell_id,
        pci_performed = (pci_count > 0), # If false, conservatively managed
        stemi = (mi_stemi_schnier_count > 0),
        nstemi = (mi_nstemi_schnier_count > 0),
        mi = (mi_schnier_count > 0)
    ) %>%
    left_join(spell_data, by = "spell_id") %>%
    rename(
        index_date = spell_start_date
    )

####### COMPUTE COUNT OF PREVIOUS DIAGNOSES AND PROCEDURES #######

# Join nhs number onto the index spells and the code_group_counts
index_spells_with_nhs_number <- index_spell_info %>%
    left_join(nhs_numbers, by = "spell_id")

code_group_counts_with_nhs_number <- code_group_counts %>%
    left_join(nhs_numbers, by = "spell_id") %>%
    # Rename the spell id here to distinguish the index spell
    # id (which is always called spell_id) from the other spells
    # before and after the index
    rename(other_spell_id = spell_id)

# Contains the index spell (spell_id), the patient's other
# spells (other_spell_id), and the duration from index to
# other spell (negative if the other spell is before the index).
spell_time_differences <- index_spells_with_nhs_number %>%
    # For each index event, join all other spells that the patient had.
    # Expect many-to-many because the same patient could have multiple index events.
    left_join(
        code_group_counts_with_nhs_number,
        by = "nhs_number", relationship = "many-to-many"
    ) %>%
    # Join on the spell data to the other spells
    left_join(spell_data, by = c("other_spell_id" = "spell_id")) %>%
    # Positive time difference for after, negative for before
    transmute(
        spell_id,
        other_spell_id,
        spell_time_difference = spell_start_date - index_date
    )

# This table contains the total number of each diagnosis and procedure
# group in a period before the index event. This could be the previous
# 12 months, excluding the month before the index event (to account for
# lack of coding data in that period)
max_period_before <- lubridate::dyears(1) # Limit count to previous 12 months
min_period_before <- lubridate::dmonths(1) # Exclude month before index (not coded yet)

counts_before_index <- spell_time_differences %>%
    # Add a mask to only include the spells in a particular window before the
    # index event (up to one year before, excluding the month before the index event
    # when data will not be available). Need to negate the time difference because
    # spells before the index have negative time.
    mutate(spell_valid_mask = if_else(
        (-spell_time_difference) > min_period_before &
            (-spell_time_difference) <= max_period_before,
        0,
        1
    )) %>%
    # Join the count information
    left_join(code_group_counts, by = c("other_spell_id" = "spell_id")) %>%
    # Do all operations per patient (and per index event for patients with multiple index events)
    group_by(spell_id) %>%
    # Sum up the counts in the valid window. By multipling the count by the valid flag (0 or 1),
    # it is only included if it came from a spell in the valid window.
    summarise(
        bleeding_al_ani_count_before = sum(bleeding_al_ani_count * spell_valid_mask),
        mi_schnier_count_before = sum(mi_schnier_count * spell_valid_mask),
        mi_stemi_schnier_count_before = sum(mi_stemi_schnier_count * spell_valid_mask),
        mi_nstemi_schnier_count_before = sum(mi_nstemi_schnier_count * spell_valid_mask),
        pci_count_before = sum(pci_count * spell_valid_mask),
    )

####### COMPUTE TIME TO FIRST BLEED AND FIRST MI #######

# Table of just the index spells which have a subsequent outcome in the
# window defined above. This is generic -- the only bit that depends on the
# column is the filter and summarise part.
index_with_subsequent_bleed <- spell_time_differences %>%
    # Join the count data for each subsequent spell (other spell)
    left_join(code_group_counts, by = c("other_spell_id" = "spell_id")) %>%
    find_subsequent_outcome(index_spell_info, "bleeding_al_ani", end_date) %>%
    add_12m_outcome("bleeding_al_ani")

index_with_subsequent_ischaemia <- spell_time_differences %>%
    # Join the count data for each subsequent spell (other spell)
    left_join(code_group_counts, by = c("other_spell_id" = "spell_id")) %>%
    find_subsequent_outcome(index_spell_info, "mi_schnier", end_date) %>%
    add_12m_outcome("mi_schnier")

# Finally, join all the index data to form the dataset
hes_spells_dataset <- index_spell_info %>%
    left_join(index_with_subsequent_bleed, by = "spell_id") %>%
    left_join(index_with_subsequent_ischaemia, by = "spell_id") %>%
    left_join(counts_before_index, by = "spell_id") %>%
    transmute(
        # Index information
        idx_date = index_date,
        idx_age = age,
        idx_gender = gender,
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
        outcome_12m_bleeding_al_ani = bleeding_al_ani_12m,
        outcome_time_mi_schnier = mi_schnier_time,
        outcome_status_mi_schnier = mi_schnier_status,
        outcome_12m_mi_schnier = mi_schnier_12m,
    )

save_dataset(hes_spells_dataset, "hes_spells_dataset")

end_time <- Sys.time()

# Calculate the script running time
end_time - start_time

####### DESCRIPTIVE ANALYSIS #######

# Proportion of index events with a PCI procedure
# (expect the majority)
p_pci_performed <- hes_spells_dataset %>%
    pull(idx_pci_performed) %>%
    mean()

# Calculate the proportion of index events with ACS (either
# STEMI or NSTEMI) (expect majority)
p_mi <- hes_spells_dataset %>%
    pull(idx_mi) %>%
    mean()

# Calculate proportion of _all_ index events that are STEMI
# or NSTEMI (note some index events are not ACS)
p_stemi <- hes_spells_dataset %>%
    pull(idx_stemi) %>%
    mean()
p_nstemi <- hes_spells_dataset %>%
    pull(idx_nstemi) %>%
    mean()

# Calculate the proportion of patients with bleeding
# events in one year. Should be around 0-5%. This estimate
# will underestimate risk due to right censoring.
p_bleed_1y_naive <- hes_spells_dataset %>%
    pull(outcome_12m_bleeding_al_ani) %>%
    mean()
