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

library(tidyverse)

con <- DBI::dbConnect(odbc::odbc(), "xsw", bigint = "character")
id <- dbplyr::in_catalog("abi", "dbo", "vw_apc_sem_spell_001")

####### GET THE RAW DATA #######

# Date range for the data. This is necessary for computing right censoring
# for the survival data. To be valid, make sure that the database contains data
# for the full date range given here.
start_date <- lubridate::ymd_hms("2020-01-01 00:00:00")
end_date <- lubridate::ymd_hms("2021-01-01 00:00:00")

# Raw spell data from the databse. This is just a spell table, so
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
al_ani_bleeding_icd10 <- c(
    "I60", "I61", "I62", "I85.0", "K22.1", "K22.6",
    "K25.0", "K25.2", "K25.4", "K25.6", "K26.0", "K26.2",
    "K26.4", "K26.6", "K27.0", "K27.2", "K27.4", "K27.6",
    "K28.0", "K28.2", "K28.4", "K28.6", "K29.0", "K31.80",
    "K63.80", "K92.0", "K92.1", "K92.2", "K55.2", "K51",
    "K57", "K62.5", "K92.0", "K92.1", "K92.2"
) %>%
    str_replace("\\.", "") %>%
    tolower()

# List of ICD-10 codes identifying ACS events
acs_stemi_icd10 <- c(
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
        acs_stemi_flag = icd10_code %in% acs_stemi_icd10,
        acs_nstemi_flag = icd10_code %in% acs_nstemi_icd10,
    ) %>%
    # Group up by spell and add up the flags, then ungroup
    group_by(spell_id) %>%
    mutate(
        bleeding_count = sum(bleeding_flag),
        acs_stemi_count = sum(acs_stemi_flag),
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
    filter(acs_stemi_count > 0 | acs_nstemi_count > 0 | pci_count > 0) %>%
    # Record whether the index event is PCI or conservatively managed (ACS)
    mutate(
        pci_performed = (pci_count > 0), # If false, conservatively managed
    ) %>%
    # Keep only relevant columns for index (others will be joined back on in next step)
    select(nhs_number, spell_id, pci_performed, age, spell_start_date) %>%
    rename(age_at_index = age, index_date = spell_start_date, index_spell_id = spell_id)

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
    # Added the bleeding occurred flag if there is a subsequent bleed
    mutate(bleed_status = if_else(n() == 2, 1, 0)) %>%
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
    select(index_date, bleed_status, bleed_time, age_at_index)

####### DESCRIPTIVE ANALYSIS #######

# Calculate what proportion of patients with bleeding
# events in one year. Should be around 0-5%.
p_one_year_bleed <- bleed_times %>%
    filter(bleed_time < lubridate::dyears(1)) %>% 
    pull(bleed_status) %>% 
    mean()




