get_code_group

##' Get a list of
get_code_groups <- function(diagnoses_file, procedures_file) {
    get_codes_in_group(diagnoses_file, "bleeding_al_ani") %>%
        bind_rows(get_codes_in_group(diagnoses_file, "mi_schnier")) %>%
        bind_rows(get_codes_in_group(diagnoses_file, "mi_stemi_schnier")) %>%
        bind_rows(get_codes_in_group(diagnoses_file, "mi_nstemi_schnier")) %>%
        # The ischaemic heart diseases group, considered by 2015 Bezin
        # et al. to be a superset of ACS (includes all codes that an
        # ACS could be coded as). As a result, it increases the chance of
        # identifying ACS index events, at the expense of including
        # some spells that are not necessarily the ACS of interest.
        bind_rows(get_codes_in_group(diagnoses_file, "ihd_bezin")) %>%
        # A smaller subset of ihd_bezin, considered to represent a good
        # compromise between the PPV for ACS and identifying ACS spells.
        bind_rows(get_codes_in_group(diagnoses_file, "acs_bezin")) %>%
        bind_rows(get_codes_in_group(procedures_file, "pci")) %>%
        # Transform all the codes to a standard form where letters are lower
        # case, there is no whitespace, and dots are removed
        mutate(name = name %>% str_replace_all("(\\.| )", "") %>% tolower())
}

##' From a table of diagnosis and procedure codes in long format,
##' associated to recor IDs (either spells or episodes), compute
##' the total number of codes in a set of specified groups, and and
##' one new column per group count.
##'
##' The function assumes that the clinical codes have had whitespace
##' removed, dots removed, and all characters converted to lower case.
##' Only exact matches of codes in the groups are considered.
count_code_groups_by_record <- function(diagnoses_and_procedures, record_id) {
    diagnosis_counts <- diagnoses_and_procedures %>%
        filter(clinical_code_type == "diagnosis") %>%
        group_by({{ record_id }}) %>%
        summarise(
            bleeding_al_ani_count = sum(clinical_code %in% bleeding_al_ani),
            mi_schnier_count = sum(clinical_code %in% mi_schnier),
            mi_stemi_schnier_count = sum(clinical_code %in% mi_stemi_schnier),
            mi_nstemi_schnier_count = sum(clinical_code %in% mi_nstemi_schnier),
            pci_count = sum(clinical_code %in% pci &
                clinical_code_type == "procedure"),
        )

    procedure_counts <- diagnoses_and_procedures %>%
        filter(clinical_code_type == "procedure") %>%
        group_by({{ record_id }}) %>%
        summarise(
            pci_count = sum(clinical_code %in% pci),
        )

    diagnosis_counts %>%
        left_join(procedure_counts, by = join_by({{ record_id }}))
}
