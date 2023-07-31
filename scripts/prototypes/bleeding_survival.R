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
# bleeding and ischaemia). Does not account for time delay in codes
# becoming available in statistical analysis.
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
# for the full date range given here.
start_date <- lubridate::ymd_hms("2020-01-01 00:00:00")
end_date <- lubridate::ymd_hms("2021-01-01 00:00:00")

# Raw spell data from the database. This is just a spell table, so
# episode information has been summarised into a single row.
raw_data <- dplyr::tbl(con, id) %>%
    select(
        AIMTC_Pseudo_NHS,
        AIMTC_Age,
        AIMTC_ProviderSpell_Start_Date,
        matches("^(Primary)?Procedure") & !contains("Date") & !contains("Scheme"),
        matches("Diagnosis") & !contains("Date") & !contains("Scheme")
    ) %>%
    rename(nhs_number = AIMTC_Pseudo_NHS, age = AIMTC_Age, spell_start_date = AIMTC_ProviderSpell_Start_Date) %>%
    filter(!is.na(nhs_number)) %>%
    filter(spell_start_date > start_date, spell_start_date < end_date) %>%
    collect() %>%
    mutate(spell_id = row_number())

# For joining NHS number by spell id later on
nhs_numbers <- raw_data %>%
    select(spell_id, nhs_number)

# For joining spell information by spell id later
spell_data <- raw_data %>%
    select(spell_id, age, spell_start_date)

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

# Derive data about the index spell from the counts
index_spell_data <- index_spells %>%
    left_join(code_group_counts, by="spell_id") %>%    
    # Record whether the index event is PCI or conservatively managed (ACS).
    # Record STEMI and NSTEMI as separate columns to account for possibility
    # of neither (i.e. no ACS).
    mutate(
        pci_performed = (pci_count > 0), # If false, conservatively managed
        stemi = (mi_stemi_schnier_count > 0),
        nstemi = (mi_nstemi_schnier_count > 0)
    ) %>%
    # Join on the index spell data and rename to refer to index
    left_join(spell_data, by = "spell_id") %>%
    rename(
        index_date = spell_start_date,
        age_at_index = age
    ) %>%
    # Drop unnecessary count columns (will be joined back later)
    select(-matches("count"))

####### COMPUTE COUNT OF PREVIOUS DIAGNOSES AND PROCEDURES #######

# Join nhs number onto the index spells and the code_group_counts
index_spells_with_nhs_number <- index_spell_data %>%
    left_join(nhs_numbers, by = "spell_id")

code_group_counts_with_nhs_number <- code_group_counts %>%
    left_join(nhs_numbers, by = "spell_id")

# All spells for each patient, with the time difference between
# the spell and the index spell
spells_relative_to_index <- index_spells_with_nhs_number %>%
    # Will need to distinguish the index spell id later
    rename(index_spell_id = spell_id) %>%
    # For each index event, join all other spells that the patient had.
    # Expect many-to-many because the same patient could have multiple index events.
    left_join(code_group_counts_with_nhs_number, by = "nhs_number", relationship = "many-to-many") %>%
    # Join on the spell data
    left_join(spell_data, by = "spell_id") %>%
    mutate(spell_time_difference = spell_start_date - index_date)
    

# This table contains the total number of each diagnosis and procedure
# group in a period before the index event. This could be the previous
# 12 months, excluding the month before the index event (to account for
# lack of coding data in that period)
max_period_before <- lubridate::dyears(1) # Limit count to previous 12 months
min_period_before <- lubridate::dmonths(1) # Exclude month before index (not coded yet)

counts_before_index <- spells_relative_to_index %>%
    # Add a mask to only include the spells in a particular window before the
    # index event (up to one year before, excluding the month before the index event
    # when data will not be available).
    mutate(spell_valid_mask = if_else(
        (-spell_time_difference) > min_period_before &
            (-spell_time_difference) <= max_period_before,
        0,
        1
    )) %>%
    # Do all operations per patient (and per index event for patients with multiple index events)
    group_by(index_spell_id) %>%
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

# Want two things for survival analysis: time to next bleed if there
# is a bleed; and maximum follow-up date for right censoring, if there is no bleed.
max_period_after <- lubridate::dyears(1) # limit outcome to 12 months after (for binary classification)
min_period_after <- lubridate::dhours(72) # Potentially exclude following 72 hours

# Table of just the index spells which have a subsequent bleed in the
# window defined above. This is generic -- the only bit that depends on the
# column is the filter and summarise part.
index_spells_with_subsequent_bleed <- spells_relative_to_index %>%
    # Add a mask to only include the spells in a particular window before the
    # index event (up to one year before, excluding the month before the index event
    # when data will not be available).
    filter(
        spell_time_difference >= min_period_after,
        spell_time_difference < max_period_after,
        bleeding_al_ani_count > 0,
    ) %>%
    transmute(
        spell_id = index_spell_id,
        bleeding_time = spell_time_difference,
    ) %>%
    # This will include a row for all subsequent bleeds.
    # Pick only the first
    group_by(spell_id) %>%
    filter(
        bleeding_time == min(bleeding_time),
        bleeding_status = 1,
    )

# Now get all the index spells where there was no subsequent bleed,
# and record the right censoring time based on the end date of the
# raw dataset
index_spells_no_subsequent_bleed <- index_spell_data %>%
    filter(!(spell_id %in% (index_spells_with_subsequent_bleed$spell_id))) %>%
    transmute(
        spell_id,
        bleeding_time = end_date - index_date, # Right-censored
        bleeding_status = 0
    )

# Join together the bleed/no-bleed rows to get all the bleeding
# survival data
index_spells_bleeding_survival <- index_spells_no_subsequent_bleed %>%
    bind_rows(index_spells_with_subsequent_bleed)


# Pick out the spells before the index event
filter(spell_time_difference < 0) %>%
    arrange(spell_time_difference, .by_group = TRUE) %>%
    slice_head(n = 2) %>%
    # Added the bleeding occurred flag if there is a subsequent
    # spell which is a bleed
    mutate(bleed_status = if_else(
        (n() == 2) & (last(bleeding_count) > 0), 1, 0
    )) %>%
    # Add the time-to-bleed, which is either the spell time difference, or
    # the maximum dataset date if right censored
    mutate(bleed_time = if_else(bleed_status == 1,
        spell_time_difference, end_date - index_date
    )) %>%
    # Want just one row per index event; currently there is either
    # one (for no bleed) or two (for a bleed). =Want to keep all
    # bleeding rows, and only index rows when there is no bleeding row.
    ungroup() %>%
    filter((index_spell_id != spell_id) | bleed_status == 0) %>%
    # There is no use for the nhs_number or index spell id (each
    # row is considered a separate event), or the spell_start_date
    select(
        index_date, bleed_status, bleed_time, age_at_index, pci_performed,
        acs_stemi_schnier, acs_nstemi
    )

####### DESCRIPTIVE ANALYSIS #######

# Check the proportion of STEMI/NSTEMI presentation. Note that
# not all rows

# Proportion of index events with a PCI procedure
# (expect the majority)
p_pci_performed <- bleed_times %>%
    pull(pci_performed) %>%
    mean()

# Calculate the proportion of index events with ACS (either
# STEMI or NSTEMI) (expect majority)
p_acs <- bleed_times %>%
    mutate(acs = (acs_stemi_schnier | acs_nstemi)) %>%
    pull(acs) %>%
    mean()

# Calculate proportion of _all_ index events that are STEMI
# or NSTEMI (note some index events are not ACS)
p_stemi <- bleed_times %>%
    pull(acs_stemi_schnier) %>%
    mean()
p_nstemi <- bleed_times %>%
    pull(acs_nstemi) %>%
    mean()

# Calculate what proportion of patients with bleeding
# events in one year. Should be around 0-5%. This estimate
# will underestimate risk due to right censoring.
p_bleed_1y_naive <- bleed_times %>%
    filter(bleed_time < lubridate::dyears(1)) %>%
    pull(bleed_status) %>%
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

sv <- Surv(bleed_times$bleed_time, bleed_times$bleed_status)
s1 <- survfit(Surv(bleed_time, bleed_status) ~ 1, data = bleed_times)

# Plot Kaplan-Meier curves
survfit2(Surv(bleed_time, bleed_status) ~ 1, data = bleed_times) %>%
    ggsurvfit() +
    # Convert x scale to days
    scale_x_continuous(labels = function(x) x / 86400) +
    labs(x = "Days", y = "Overall survival probability") +
    add_confidence_interval() +
    add_risktable()

# Find the bleeding risk at one year. This shows the survival
# probability at one year, along with upper and lower confidence
# intervals.
one_year_risk <- summary(survfit(Surv(bleed_time, bleed_status) ~ 1, data = bleed_times),
    times = 365 * 24 * 60 * 60
)

# Get one year risk of bleed
p_bleed_1y <- 1 - one_year_risk$surv

# Upper and lower CI are swapped (because they are survival)
p_bleed_one_year_upper <- 1 - one_year_risk$lower # Lower CI, 95%
p_bleed_one_year_lower <- 1 - one_year_risk$upper # Upper CI, 95%

# Show survival in table
survfit(Surv(bleed_time, bleed_status) ~ 1, data = bleed_times) %>%
    tbl_survfit(
        times = 365 * 24 * 60 * 60,
        label_header = "**1-year survival (95% CI)**"
    )

####### SURVIVAL ANALYSIS (AGE INPUT) #######

coxph(Surv(bleed_time, bleed_status) ~ age_at_index, data = bleed_times)

survdiff(Surv(bleed_time, bleed_status) ~ age_at_index,
    data = bleed_times
)

# Show the regression results as a table
coxph(
    Surv(bleed_time, bleed_status) ~ age_at_index
        + pci_performed + acs_stemi_schnier + acs_nstemi,
    data = bleed_times
) %>%
    tbl_regression(exp = TRUE)
