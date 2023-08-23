##' Get patient demographic information (age and gender)
get_demographics <- function(con) {
    demographics_id <- dbplyr::in_catalog("HIC_COVID_JS", "dbo", "cv_covid_demographics")
    dplyr::tbl(con, demographics_id) %>%
        select(
            Subject, # Patient identifier
            gender_desc,
            age, # At time of data collection, 2021
            ethnicity_desc,
        ) %>%
        rename(
            patient_id = Subject,
            gender = gender_desc,
            age_in_2021 = age,
            ethnicity = ethnicity_desc,
        ) %>%
        collect() %>%
        mutate(gender = case_when(
            gender == "Female" ~ "female",
            gender == "Male" ~ "male",
            TRUE ~ "unknown",
        ))
}

get_admission_medication <- function(con) {
    prescriptions_admission_id <- dbplyr::in_catalog("HIC_COVID_JS", "dbo", "cv_covid_pharmacy_administration")
    dplyr::tbl(con, prescriptions_admission_id) %>%
        select(
            IP_SPELL_ID, # Link to the spell ID in the episodes table
            medication_name,
            dosage_unit,
            `Medication - Frequency`,
            route,
            `Medication - On Admission`
        ) %>%
        rename(
            spell_id = IP_SPELL_ID,
            medication = medication_name,
            dose = `dosage_unit`,
            frequency = `Medication - Frequency`,
            action_on_admission = `Medication - On Admission`,
        ) %>%
        filter(!is.na(spell_id)) %>%
        collect()
}

get_discharge_medication <- function(con) {
    prescriptions_discharge_id <- dbplyr::in_catalog("HIC_COVID_JS", "dbo", "cv_covid_pharmacy_discharge")
    dplyr::tbl(con, prescriptions_discharge_id) %>%
        select(
            spell_id,
            medication_name,
            ordered_dose,
            ordered_frequency,
            ordered_route,
            prescription_type,
        ) %>%
        rename(
            medication = medication_name,
            dose = ordered_dose,
            frequency = ordered_frequency,
            route = ordered_route,
            type = prescription_type,
        )%>%
        filter(!is.na(spell_id)) %>%
        collect()
}

##' Get a list of blood test results
get_blood_tests_hic <- function(con, start_date, end_date) {
    pathology_blood_id <- dbplyr::in_catalog("HIC_COVID_JS", "dbo", "cv_covid_pathology_blood")
    dplyr::tbl(con, pathology_blood_id) %>%
        select(
            subject, # Patient identifier
            order_name,
            test_name,
            test_result,
            test_result_unit,
            sample_collected_date_time,
            result_available_date_time,
        ) %>%
        rename(
            patient_id = subject,
            family = order_name,
            test = test_name,
            result = test_result,
            unit = test_result_unit,
            sample_collected = sample_collected_date_time,
            result_available = result_available_date_time
        ) %>%
        filter(!is.na(patient_id)) %>%
        filter(sample_collected > start_date, sample_collected < end_date) %>%
        collect()
}

##' Get a list of episodes, along with the corresponding spell identifier,
##' the patient identifier, and the episode and spell start date
get_episodes_hic <- function(con, start_date, end_date) {
    episodes_id <- dbplyr::in_catalog("HIC_COVID_JS", "dbo", "cv_covid_episodes")
    dplyr::tbl(con, episodes_id) %>%
        select(
            episode_identifier, # Key for the diagnosis and procedure tables
            subject, # Patient identifier
            spell_identifier,
            # Taking hospital arrival time as spell start time for the purpose
            # of calculating time-to-subsequent events
            arrival_dt_tm,
            episode_start_time,
            episode_end_time,
        ) %>%
        rename(
            episode_id = episode_identifier,
            patient_id = subject,
            spell_id = spell_identifier,
            spell_start_date = arrival_dt_tm,
            episode_start_date = episode_start_time,
            episode_end_date = episode_end_time,
        ) %>%
        filter(!is.na(patient_id)) %>%
        filter(spell_start_date > start_date, spell_start_date < end_date) %>%
        collect()
}

##' Get a table of diagnosis (ICD-10) and procedure (OPCS-4) codes from
##' the HIC database. The table is in long format, with one column for
##' episode ID, a column for the code itself, and a column to indicate
##' whether the code is a diagnosis or a procedure (because some codes
##' overlap).
##'
##' Diagnosis codes are converted to lower case, whitespace is stripped,
##' and the dot is removed.
##'
get_diagnoses_and_procedures_hic <- function(con) {
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

    # Collect together all the diagnosis and procedure information
    # into a single table in long format, along with the episode id
    raw_diagnoses_data %>%
        bind_rows(raw_procedures_data) %>%
        mutate(clinical_code = clinical_code %>% str_replace_all("(\\.| )", "") %>% tolower())
}
