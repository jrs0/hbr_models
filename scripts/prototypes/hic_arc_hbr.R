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

# Date range for the data. Set a date range outside the date range
# of the dataset to collect all data.
start_date <- lubridate::ymd_hms("2015-01-01 00:00:00")
# Go careful with the end date -- data must be present in the
# dataset up the the end date (for right censoring). Should really
# compute right censor date from last seen date in the data
end_date <- lubridate::ymd_hms("2024-01-01 00:00:00")

####### DATABASE CONNECTION

con <- DBI::dbConnect(odbc::odbc(), "hic", bigint = "character")

####### GET THE RAW DATA FOR DIAGNOSES AND PROCEDURES #######

# In this dataset, diagnosis and precedure information is held across
# three tables: one for episodes (with a primary key), and two others
# containing the diagnoses and procedures in long format.

raw_episodes_data <- get_episodes_hic(con, start_date, end_date)

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

# Single column of all episodes in the dataset
all_episodes <- raw_episodes_data %>%
    select(episode_id)

# Mapping from episode_id to patient. Required later for joining
# episodes together from different tables by patient.
patients <- raw_episodes_data %>%
    select(episode_id, patient_id)

# Get a long list of clinical codes (ICD-10 and OPCS-4) for each episode
# (there are multiple codes per episode)
raw_diagnoses_and_procedures <- get_diagnoses_and_procedures_hic(con)

####### COUNT THE OCCURANCES OF CODES IN EACH GROUP #######

# Get the code groups that are in the codes files
code_groups <- get_code_groups("../codes_files/icd10.yaml", "../codes_files/opcs4.yaml")

# Reduce the diagnosis and procedures to a total count in each group by
# episode id.
code_group_counts <- raw_diagnoses_and_procedures %>%
    count_code_groups_by_record(episode_id, code_groups)

####### DEMOGRAPHICS #######

raw_demographics <- get_demographics(con)

####### MEDICATION INFORMATION #######

raw_admission_medication <- get_admission_medication(con)
raw_discharge_medication <- get_discharge_medication(con)

continued_medication <- raw_admission_medication %>%
    filter(action_on_admission == "Continued") %>%
    transmute(
        spell_id,
        medication = tolower(medication),
        route = tolower(route),
        new_or_continued = "continued",
    )

new_medication <- raw_discharge_medication %>%
    transmute(
        spell_id,
        medication = tolower(medication),
        route = tolower(route),
        new_or_continued = "new"
    )

# Medication that is present on discharge is both medication
# on admission that is "Continued", or new medication that is
# prescribed on discharge. This table does not contain any
# dose or frequency information, but does include the route.
# Note that, depending on exactly how the continued medication
# is recorded in the discharge medication table, this table may
# contain duplicate medication (medication in the same spell marked
# as both new and continued). Do not depend on medication counts
# (only use medication presence).
medication_present_on_discharge <- continued_medication %>%
    bind_rows(new_medication)

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
    # Pick a value strictly larger than 90 to use as the
    # representative for >90 class.
    mutate(result = str_replace(result, ">90", "91")) %>%
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

# The steps below calculate the ARC-HBR score locally to
# each episode (even for the scores which refer to a period
# of time). This is a step in the full calculation for each
# epsiode, which may aggregate scores from previous episodes.

# Anaemia
# - For men and women, major (1) if Hb < 110 g/L
# - For women, minor (0.5) if Hb < 119 g/L
# - For men, minor (0.5) if Hb < 129 g/L
# - 0 otherwise
#
# The calculation interpretes the criterion as baseline
# anaemia, i.e. before the PCI (not explicitly stated in
# the ARC HBR definition). See comments for TCP below.
#
# "Anemia ... is frequently encountered in patients
# undergoing PCI, with a reported prevalence of 21.6%
# in the Bern DES Registry" (Urban et al., 2019), so
# expect mean of arc_hbr_anaemia != 0 column
# approx. 0.22.
#
arc_hbr_anaemia <- blood_tests %>%
    # Reduce to the tests of interest
    filter(test == "Haemoglobin") %>%
    # Reduce by taking the _first_ Hb count reading
    # (approximation to baseline) within in episode
    arrange(episode_id, sample_collected) %>%
    group_by(episode_id) %>%
    summarise(first_result = first(result)) %>%
    # Need patient gender from demographics
    left_join(raw_episodes_data, by = "episode_id") %>%
    left_join(raw_demographics, by = "patient_id") %>%
    # Calculate the ARC HBR criterion for each blood test
    mutate(arc_hbr_anaemia = case_when(
        first_result < 110 ~ 1,
        (gender == "female") & (first_result) < 119 ~ 0.5,
        (gender == "male") & (first_result < 129) ~ 0.5,
        TRUE ~ 0,
    )) %>%
    select(
        episode_id,
        arc_hbr_anaemia
    ) %>%
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
    summarise(first_result = first(result)) %>%
    # Calculate the ARC HBR criterion for each episode
    mutate(arc_hbr_tcp = case_when(
        (first_result < 100) ~ 1,
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

# Chronic Kidney Disease (CKD)
# Severe (stage 4) or end-stage (stage 5)
# CKD is a major ARC HBR criterion. Moderate
# (stage 3) CKD is a minor criterion. See
# below for definitions.
#
# Stage 5: eGFR < 15 mL/min
# Stage 4: eGFR < 30 mL/min
# Stage 3: eGFR < 60 mL/min
#
# As a result:
# - Major (1) if eGFR < 30
# - Minor (0.5) if eGFR < 60
# - 0 otherwise
#
# "Approximately 30% of patients undergoing PCI
# have an eGFR <60 mL/min", (Urban et al., 2019),
# so expect mean of arc_hbr_tcp column approx.
# 0.3.
#
arc_hbr_ckd <- blood_tests %>%
    filter(test == "eGFR") %>%
    # Reduce by taking the _first_ platelet count reading,
    #
    arrange(episode_id, sample_collected) %>%
    group_by(episode_id) %>%
    summarise(first_result = first(result)) %>%
    # Calculate the ARC HBR criterion for each episode
    mutate(arc_hbr_ckd = case_when(
        (first_result < 30) ~ 1,
        (first_result < 60) ~ 0.5,
        TRUE ~ 0,
    )) %>%
    select(
        episode_id,
        arc_hbr_ckd
    ) %>%
    # Join on all the episodes that did not have any blood test
    # results (will right join as NA) and replace the
    # NA with zero to indicate no HBR criterion.
    right_join(all_episodes, by = "episode_id") %>%
    mutate(arc_hbr_ckd = replace_na(arc_hbr_ckd, 0))

# Age
# - Minor (0.5) if age >= 75
# - 0 otherwise
#
# The age in the demographics data was the patient
# age when data was collected (2021). Ages must be
# recomputed based on this date
age_baseline_date <- lubridate::ymd_hms("2021-1-1 00:00:00")
arc_hbr_age <- raw_episodes_data %>%
    left_join(raw_demographics, by = "patient_id") %>%
    mutate(
        age = age_in_2021 +
            (episode_start_date - age_baseline_date) /
                lubridate::dyears(1)
    ) %>%
    transmute(
        episode_id,
        arc_hbr_age = if_else(age >= 75, 0.5, 0)
    )

# Long-term use of OAC
#
# Anticipated use of long-term oral anticoagulants is
# considered a major criterion. The presence of one of
# the following drugs in either the continued admission
# medication or discharge medication is used as a proxy
# for "anticipated long-term use":
#
# - Warfarin (vitamin K antagonist)
# - Apixaban, dabigatran, edoxaban, rivaroxaban (direct
#   oral anticoagulants)
#
# Medication is only considered if it is orally administered
# (excludes jejunoenteral and subcutaneous, and NA)
arc_hbr_oac <- raw_episodes_data %>%
    # Join the new and continued medication on discharge
    left_join(
        medication_present_on_discharge,
        by = "spell_id", relationship = "many-to-many"
    ) %>%
    # Pick out only the relevant orally administered drugs
    filter(
        str_detect(
            medication,
            # Do not depend on medication column having these
            # exact names -- for example, "warfarin sodium" is present
            "(warfarin|apixaban|dabigatran|edoxaban|rivaroxaban)",
        ),
        route == "oral"
    ) %>%
    # All these rows are episodes with an OAC -- mark them as
    # ARC-HBR major
    distinct(episode_id) %>%
    mutate(arc_hbr_oac = 1) %>%
    # Join on all the episodes that did not have any OAC
    # prescribed (will right join as NA) and replace the
    # NA with zero to indicate no HBR criterion.
    right_join(all_episodes, by = "episode_id") %>%
    mutate(arc_hbr_oac = replace_na(arc_hbr_oac, 0))

####### MAKE ARC SCORE TABLE #######

# This is a table of what HBR criteria occurred in every episode
# in the dataset. It is not strictly the ARC-HBR score, because that
# involves calculating whether ARC criteria occurred in a time frame.

arc_hbr <- arc_hbr_age %>%
    left_join(arc_hbr_oac, by = "episode_id") %>%
    left_join(arc_hbr_ckd, by = "episode_id") %>%
    left_join(arc_hbr_anaemia, by = "episode_id") %>%
    #left_join(arc_hbr_transfusion, by = "episode_id") %>%
    left_join(arc_hbr_tcp, by = "episode_id")
    #left_join(arc_hbr_cbd, by = "episode_id") %>%
    #left_join(arc_hbr_transfusion, by = "episode_id") %>%
    #left_join(arc_hbr_cph, by = "episode_id") %>%
    #left_join(arc_hbr_cancer, by = "episode_id") %>%
    #left_join(arc_hbr_stroke_ich, by = "episode_id") %>%
    #left_join(arc_hbr_surgery_after_pci, by = "episode_id") %>%
    #left_join(arc_hbr_surgery_before_pci, by = "episode_id") %>%
    #left_join(arc_hbr_nsaid_steroid, by = "episode_id") %>%

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
    filter(acs_bezin_count > 0 | pci_count > 0) %>%
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
        mi = (mi_schnier_count > 0),
        acs = (acs_bezin_count > 0)
    )