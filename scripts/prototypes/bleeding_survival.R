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

####### DEFINE ICD-10 and OPCS-4 CODE GROUPS #######

# List of ICD-10 codes that defines a bleeding event
bleeding_al_ani <- get_codes_in_group("../codes_files/icd10.yaml", "bleeding_al_ani") %>%
    pull(name) %>%
    str_replace("\\.", "") %>%
    tolower()

# List of ICD-10 codes identifying ACS events
acs_stemi_schnier_icd10 <- c(
    "I21.0", "I21.1", "I21.2", "I21.3", "I22.0", "I22.1", "I22.8"
) %>%
    str_replace("\\.", "") %>%
    tolower()
acs_nstemi_icd10 <- c(
    "I21.4", "I22.9"
) %>%
    str_replace("\\.", "") %>%
    tolower()

# List of OPCS-4 codes identifying PCI procedures
pci_opcs4 <- c(
    "K49.1", "K49.2", "K49.3", "K49.4", "K49.8", "K49.9",
    "K50.1", "K50.2", "K50.3", "K50.4", "K50.8", "K50.9",
    "K75.1", "K75.2", "K75.3", "K75.4", "K75.8", "K75.9"
) %>%
    str_replace("\\.", "") %>%
    tolower()

####### COUNT UP OCCURRENCES OF CODE GROUPS IN EACH SPELL #######

# The goal is to merge all of the diagnoses into a single column
with_diagnoses <- raw_data %>%
    pivot_longer(
        matches("Diagnosis") & !contains("Date") & !contains("Scheme"),
        names_to = "diagnosis_position", values_to = "icd10_code"
    ) %>%
    # Convert the ICD10 codes to lower case, remove dot, and remove whitespace
    mutate(icd10_code = icd10_code %>% str_replace_all("(\\.| )", "") %>% tolower()) %>%
    # Add a flag indicating whether a code is in a group
    mutate(
        bleeding_flag = icd10_code %in% al_ani_bleeding_icd10,
        acs_stemi_schnier_flag = icd10_code %in% acs_stemi_schnier_icd10,
        acs_nstemi_flag = icd10_code %in% acs_nstemi_icd10,
    ) %>%
    # Group up by spell and add up the flags, then ungroup
    group_by(spell_id) %>%
    mutate(
        bleeding_count = sum(bleeding_flag),
        acs_stemi_schnier_count = sum(acs_stemi_schnier_flag),
        acs_nstemi_count = sum(acs_nstemi_flag),
    ) %>%
    # Drop the flag columns and icd10 code, and pick just the first
    # row of each group (any row will do, they all have the same counts)
    select(-matches("flag"), -icd10_code) %>%
    slice_head(n = 1)

# Now do the same for procedures
with_diagnoses_and_procedures <- with_diagnoses %>%
    pivot_longer(
        matches("^(Primary)?Procedure") & !contains("Date") & !contains("Scheme"),
        names_to = "procedure_position", values_to = "opcs4_code"
    ) %>%
    # Convert the OPCS-4 codes to lower case, remove dot, and remove whitespace
    mutate(opcs4_code = opcs4_code %>% str_replace_all("(\\.| )", "") %>% tolower()) %>%
    # Add a flag indicating whether a code is in a group
    mutate(
        pci_flag = opcs4_code %in% pci_opcs4,
    ) %>%
    # Group up by spell and add up the flags, then ungroup
    group_by(spell_id) %>%
    mutate(
        pci_count = sum(pci_flag),
    ) %>%
    # Drop the flag columns and icd10 code, and pick just the first
    # row of each group (any row will do, they all have the same counts)
    select(-matches("flag"), -opcs4_code) %>%
    slice_head(n = 1)

# Only keep the count columns, drop all raw diagnoses and procedures
with_relevant_columns <- with_diagnoses_and_procedures %>%
    select(-matches("(rocedure|iagnosis)"))

####### GET THE INDEX EVENTS (ACS OR PCI SPELL) #######

# Note that the spell start date is used as the index date.

# Get the spell id of index spells
index_spells <- with_relevant_columns %>%
    filter(acs_stemi_schnier_count > 0 | acs_nstemi_count > 0 | pci_count > 0) %>%
    # Record whether the index event is PCI or conservatively managed (ACS).
    # Record STEMI and NSTEMI as separate columns to account for possiblity
    # of neither (i.e. no ACS).
    mutate(
        pci_performed = (pci_count > 0), # If false, conservatively managed
        acs_stemi_schnier = (acs_stemi_schnier_count > 0),
        acs_nstemi = (acs_nstemi_count > 0)
    ) %>%
    # Keep only relevant columns for index (others will be joined back on in next step)
    select(
        nhs_number, spell_id, pci_performed, acs_stemi_schnier, acs_nstemi,
        age, spell_start_date
    ) %>%
    rename(
        age_at_index = age, index_date = spell_start_date,
        index_spell_id = spell_id
    )

####### COMPUTE TIME TO BLEED #######

# Want two things for survival analysis: time to next bleed if there
# is a bleed; and maximum follow-up date for right censoring, if there is no bleed.

bleed_times <- index_spells %>%
    # Expect many-to-many because the same patient could have multiple index events
    left_join(with_relevant_columns, by = "nhs_number", relationship = "many-to-many") %>%
    mutate(spell_time_difference = spell_start_date - index_date) %>%
    # Do all operations per patient (and per index event for patients with multiple index events)
    group_by(nhs_number, index_spell_id) %>%
    # Pick out just the index and first subsequent bleeding row (if there is one)
    filter(spell_time_difference >= 0) %>%
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
