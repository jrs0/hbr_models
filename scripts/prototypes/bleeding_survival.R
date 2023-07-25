# Prototype script for survival analysis on bleeding events following
# PCI procedures and ACS diagnoses

con <- DBI::dbConnect(odbc::odbc(), "xsw", bigint = "character")
id <- dbplyr::in_catalog("abi", "dbo", "vw_apc_sem_spell_001")

# Raw spell data from the databse. This is just a spell table, so
# episode information has been summarised into a single row.
raw_data <- dplyr::tbl(con, id) %>%
    dplyr::select(
        AIMTC_Pseudo_NHS,
        AIMTC_Age,
        AIMTC_ProviderSpell_Start_Date,
        matches("^(Primary)?Procedure") & !contains("Date") & !contains("Scheme"),
        matches("Diagnosis") & !contains("Date") & !contains("Scheme")
    ) %>%
    rename(nhs_number = AIMTC_Pseudo_NHS, age = AIMTC_Age, spell_start_date = AIMTC_ProviderSpell_Start_Date) %>%
    filter(!is.na(nhs_number)) %>%
    head(100) %>%
    collect() %>%
    mutate(spell_id = row_number())

# List of ICD-10 codes that defines a bleeding event
al_ani_icd10 <- c(
    "I60", "I61", "I62", "I85.0", "K22.1", "K22.6",
    "K25.0", "K25.2", "K25.4", "K25.6", "K26.0", "K26.2",
    "K26.4", "K26.6", "K27.0", "K27.2", "K27.4", "K27.6",
    "K28.0", "K28.2", "K28.4", "K28.6", "K29.0", "K31.80",
    "K63.80", "K92.0", "K92.1", "K92.2", "K55.2", "K51",
    "K57", "K62.5", "K92.0", "K92.1", "K92.2"
) %>%
    str_replace("\\.", "") %>%
    tolower()


# The goal is to merge all pf the diagnoses into a single column
with_bleeding <- raw_data %>%
    pivot_longer(
        matches("Diagnosis") & !contains("Date") & !contains("Scheme"),
        names_to = "diagnosis_position", values_to = "icd10_code"
    ) %>%
    # Convert the ICD10 codes to lower case, remove dot, and remove whitespace
    mutate(icd10_code = icd10_code %>% str_replace("\\.", "") %>% tolower()) %>% 
    # Group by spell to calculate
    group_by(spell_id) %>% 
    