##' Get a list of episodes, along with the corresponding spell identifier,
##' the patient identifier, and the episode and spell start date
get_episodes_hic <- function(con, start_date, end_date) {
    dplyr::tbl(con, episodes_id) %>%
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
get_diagnoses_long_hic <- function(con) {
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
