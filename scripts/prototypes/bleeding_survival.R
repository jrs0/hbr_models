# Prototype script for survival analysis on bleeding and thrombotic events
# following PCI procedures and ACS diagnoses.
#
# Purpose: to use data from the HES spells table (ICD-10 diagnoses
# and OPCS-4 procedures) to obtain time-to-bleed and time-to-ischaemia
# for ACS and PCI patients, in order to estimate the two risks using
# survival analysis
#
# Limitations: spells table is used, not episodes. Spells are obtained
# from episodes by a summarizing process which probably drops some of
# the codes. No attempt is made to use the structure of the episodes
# and spells for any purpose (e.g. primary vs. secondary). Code lists
# may not map exactly to the endpoint of interest (clinically relevant
# bleeding and ischaemia).
#
# Run this script from the directory containing the script source in
# this repository (or ensure the path to icd10.yaml and opcs4.yaml are
# correct).
#

library(tidyverse)

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
end_date <- lubridate::ymd_hms("2021-01-01 00:00:00")

# Raw spell data from the database. This is just a spell table, so
# episode information has been summarised into a single row.
raw_data <- dplyr::tbl(con, id) %>%
    select(
        AIMTC_Pseudo_NHS,
        AIMTC_Age,
        AIMTC_ProviderSpell_Start_Date,
        Sex,
        matches("^(Primary)?Procedure") & !contains("Date") & !contains("Scheme"),
        matches("Diagnosis") & !contains("Date") & !contains("Scheme")
    ) %>%
    rename(
        nhs_number = AIMTC_Pseudo_NHS,
        age = AIMTC_Age,
        gender = Sex,
        spell_start_date = AIMTC_ProviderSpell_Start_Date
    ) %>%
    filter(!is.na(nhs_number)) %>%
    filter(spell_start_date > start_date, spell_start_date < end_date) %>%
    collect() %>%
    mutate(spell_id = row_number())

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


find_subsequent_outcome <- function(
    spell_time_differences_and_counts,
    index_spell_info,
    outcome_name) {
    # Get the outcome name from the outcome_count variable. The
    # variable will have a name ending in "_count", which should be
    # removed to form the outcome_name


    # Want two things for survival analysis: time to next bleed if there
    # is a bleed; and maximum follow-up date for right censoring, if there is no bleed.
    max_period_after <- lubridate::dyears(1) # limit outcome to 12 months after (for binary classification)
    min_period_after <- lubridate::dhours(72) # Potentially exclude following 72 hours

    outcome_time <- paste0(outcome_name, "_time")
    outcome_status <- paste0(outcome_name, "_status")
    outcome_count <- as.symbol(paste0(outcome_name, "_count"))

    # Table of just the index spells which have a subsequent outcome in the
    # window defined above. This is generic -- the only bit that depends on the
    # column is the filter and summarise part.
    index_with_subsequent_outcome <- spell_time_differences_and_counts %>%
        # Only keep other spells where the bleeding count is non-zero
        # and the spell occurred in the correct window after the index
        filter(
            spell_time_difference >= min_period_after,
            spell_time_difference < max_period_after,
            !!outcome_count > 0,
        ) %>%
        # Group by the index event and pick the first bleeding event
        group_by(spell_id) %>%
        summarise(
            # Note comment above -- might accidentally include
            # the index (to fix)
            !!outcome_time := min(spell_time_difference),
            !!outcome_status := 1,
        )

    # Now get all the index spells where there was no subsequent bleed,
    # and record the right censoring time based on the end date of the
    # raw dataset
    index_no_subsequent_outcome <- index_spell_info %>%
        filter(!(spell_id %in% (index_with_subsequent_outcome$spell_id))) %>%
        transmute(
            spell_id,
            !!outcome_time := end_date - index_date, # Right-censored
            !!outcome_status := 0
        )

    # Join together the bleed/no-bleed rows to get all the bleeding
    # survival data
    index_no_subsequent_outcome %>%
        bind_rows(index_with_subsequent_outcome)
}

##' Adds a column for whether the outcome occurred at 12 months, using
##' the survival time and status columns. The new column is 1 if the
##' status is 1 for survival time less than 12 months; 0 otherwise.
add_12m_outcome <- function(index_with_subsequent_outcome, outcome_name) {
    twelve_months <- lubridate::dyears(1)

    outcome_time <- as.symbol(paste0(outcome_name, "_time"))
    outcome_status <- as.symbol(paste0(outcome_name, "_status"))
    outcome_12m <- paste0(outcome_name, "_12m")

    index_with_subsequent_outcome %>%
        mutate(!!outcome_12m := if_else(
            (!!outcome_time < twelve_months) & (!!outcome_status == 1),
            1,
            0
        ))
}

# Table of just the index spells which have a subsequent outcome in the
# window defined above. This is generic -- the only bit that depends on the
# column is the filter and summarise part.
index_with_subsequent_bleed <- spell_time_differences %>%
    # Join the count data for each subsequent spell (other spell)
    left_join(code_group_counts, by = c("other_spell_id" = "spell_id")) %>%
    find_subsequent_outcome(index_spell_info, "bleeding_al_ani") %>%
    add_12m_outcome("bleeding_al_ani")
    
index_with_subsequent_ischaemia <- spell_time_differences %>%
    # Join the count data for each subsequent spell (other spell)
    left_join(code_group_counts, by = c("other_spell_id" = "spell_id")) %>%
    find_subsequent_outcome(index_spell_info, "mi_schnier") %>%
    add_12m_outcome("mi_schnier")

# Finally, join all the index data to form the dataset
dataset <- index_spell_info %>%
    left_join(index_with_subsequent_bleed, by = "spell_id") %>%
    left_join(index_with_subsequent_ischaemia, by = "spell_id") %>%
    left_join(counts_before_index, by = "spell_id")

####### DESCRIPTIVE ANALYSIS #######

# Check the proportion of STEMI/NSTEMI presentation. Note that
# not all rows

# Proportion of index events with a PCI procedure
# (expect the majority)
p_pci_performed <- dataset %>%
    pull(pci_performed) %>%
    mean()

# Calculate the proportion of index events with ACS (either
# STEMI or NSTEMI) (expect majority)
p_mi <- dataset %>%
    pull(mi) %>%
    mean()

# Calculate proportion of _all_ index events that are STEMI
# or NSTEMI (note some index events are not ACS)
p_stemi <- dataset %>%
    pull(stemi) %>%
    mean()
p_nstemi <- dataset %>%
    pull(nstemi) %>%
    mean()

# Calculate the proportion of patients with bleeding
# events in one year. Should be around 0-5%. This estimate
# will underestimate risk due to right censoring.
p_bleed_1y_naive <- dataset %>%
    filter(bleeding_time < lubridate::dyears(1)) %>%
    pull(bleeding_status) %>%
    mean()

####### END OF DATA PREPROCESSING #######

# At this point, expecting to have a dataframe bleed_times with the following
# columns. (Note: if neither acs_stemi_schnier nor acs_nstemi are true, index did not
# contain an ACS.
#
# General information:
# - index_date: what was the index event start date
# Outcomes:
# - bleed_status: whether a bleed occurred (right-censored)
# - bleed_time: time to bleed if occurred, or time to end_date if no bleed
# Predictors:
# - age_at_index:
# - pci_performed: whether index included PCI procedures
# - acs_stemi_schnier: If index was ACS STEMI
# - acs_nstemi: If index was ACS NSTEMI
#


####### SURVIVAL ANALYSIS (OVERALL) #######

library(survival)
library(ggsurvfit)
library(gtsummary)

sv <- Surv(dataset$bleeding_time, dataset$bleeding_status)
s1 <- survfit(Surv(bleeding_time, bleeding_status) ~ 1, data = dataset)

# Plot Kaplan-Meier curves
survfit2(Surv(bleeding_time, bleeding_status) ~ 1, data = dataset) %>%
    ggsurvfit() +
    # Convert x scale to days
    scale_x_continuous(labels = function(x) x / 86400) +
    labs(x = "Days", y = "Overall survival probability") +
    add_confidence_interval() +
    add_risktable()

# Find the bleeding risk at one year. This shows the survival
# probability at one year, along with upper and lower confidence
# intervals.
one_year_risk <- summary(survfit(Surv(bleeding_time, bleeding_status) ~ 1, data = dataset),
    times = 365 * 24 * 60 * 60
)

# Get one year risk of bleed
p_bleed_1y <- 1 - one_year_risk$surv

# Upper and lower CI are swapped (because they are survival)
p_bleed_one_year_upper <- 1 - one_year_risk$lower # Lower CI, 95%
p_bleed_one_year_lower <- 1 - one_year_risk$upper # Upper CI, 95%

# Show survival in table
survfit(Surv(bleeding_time, bleeding_status) ~ 1, data = dataset) %>%
    tbl_survfit(
        times = 365 * 24 * 60 * 60,
        label_header = "**1-year survival (95% CI)**"
    )

####### SURVIVAL ANALYSIS (AGE INPUT) #######

coxph(Surv(bleeding_time, bleeding_status) ~ age_at_index, data = dataset)

survdiff(Surv(bleeding_time, bleeding_status) ~ age_at_index,
    data = dataset
)

# Show the regression results as a table
coxph(
    Surv(bleeding_time, bleeding_status) ~ age_at_index
        + pci_performed + stemi + nstemi,
    data = dataset
) %>%
    tbl_regression(exp = TRUE)
