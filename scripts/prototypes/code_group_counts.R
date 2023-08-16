##' Helper function to get the list of codes in a group, and append
##' columns for the group name and whether it is a diagnosis or
##' procedure group
get_single_code_group <- function(codes_file, code_group, diagnosis_or_procedure) {
    get_codes_in_group(codes_file, code_group) %>%
        mutate(group = code_group, type = diagnosis_or_procedure)
}

##' Get a tibble of the diagnosis (ICD-10) and procedure (OPCS-4) groups used in
##' the analysis. The resulting table has four columns:
##'
##' - name: the code itself (letters are lowercase, no dots, no whitespace)
##' - docs: the string description of the code
##' - group: the name of the group that this code belongs to
##' - type: either "diagnosis" (for ICD-10) or "procedure" (for OPCS-4)
##'
##' Note that the same code can appear in multiple rows, when it is in
##' multiple groups (one row per group).
get_code_groups <- function(diagnoses_file, procedures_file) {
    get_single_code_group(diagnoses_file, "bleeding_al_ani", "diagnosis") %>%
        bind_rows(get_single_code_group(diagnoses_file, "mi_schnier", "diagnosis")) %>%
        bind_rows(get_single_code_group(diagnoses_file, "mi_stemi_schnier", "diagnosis")) %>%
        bind_rows(get_single_code_group(diagnoses_file, "mi_nstemi_schnier", "diagnosis")) %>%
        # The ischaemic heart diseases group, considered by 2015 Bezin
        # et al. to be a superset of ACS (includes all codes that an
        # ACS could be coded as). As a result, it increases the chance of
        # identifying ACS index events, at the expense of including
        # some spells that are not necessarily the ACS of interest.
        bind_rows(get_single_code_group(diagnoses_file, "ihd_bezin", "diagnosis")) %>%
        # A smaller subset of ihd_bezin, considered to represent a good
        # compromise between the PPV for ACS and identifying ACS spells.
        bind_rows(get_single_code_group(diagnoses_file, "acs_bezin", "diagnosis")) %>%
        bind_rows(get_single_code_group(procedures_file, "pci", "procedure")) %>%
        # Transform all the codes to a standard form where letters are lower
        # case, there is no whitespace, and dots are removed
        mutate(name = name %>% str_replace_all("(\\.| )", "") %>% tolower())
}

##' Get the codes in a group as a list
get_codes_in_group <- function(code_groups, group_name) {
    code_groups %>%
        filter(group == group_name) %>%
        pull(name)
}

##' Get a list of all the code groups of a particular type
##' (either diagnosis or procedure). Returns a named list
##' of code lists, where each name is a code group and the
##' corresponding item in the list if the list of code names.
##' Used as a helper in counting instances of code occurances.
get_code_lists <- function(code_groups, group_type) {
    code_group_names <- code_groups %>%
        filter(type == group_type) %>%
        distinct(group) %>%
        pull(group)

    code_lists <- code_group_names %>%
        map(~ get_codes_in_group(code_groups, .x))

    names(code_lists) <- code_group_names
    code_lists
}

##' From a table of diagnosis and procedure codes in long format,
##' associated to record IDs (either spells or episodes), compute
##' the total number of codes in a set of specified groups, and and
##' one new column per group count.
##'
##' The function assumes that the clinical codes have had whitespace
##' removed, dots removed, and all characters converted to lower case.
##' Only exact matches of codes in the groups are considered.
count_code_groups_by_record <- function(diagnoses_and_procedures, record_id, code_groups) {
    # Get the list of diagnosis code groups and convert it into
    # a form that can be used as the argument to summarise
    diagnosis_code_lists <- get_code_lists(code_groups, "diagnosis")

    # Append a new column for each code group, marking whether the
    # code belongs to the group (true/false)
    diagnosis_group_counts <- list(names(diagnosis_code_lists), diagnosis_code_lists) %>%
        pmap(~ raw_diagnoses_and_procedures %>%
            mutate(code_match = (clinical_code %in% .y) & (clinical_code_type == "diagnosis")) %>%
            group_by(episode_id) %>%
            summarise(!!paste0(.x, "_count") := sum(code_match))) %>%
        reduce(left_join) 

    count_args <- list(names(diagnosis_code_lists), diagnosis_code_lists) %>%
        pmap(~ rlang::expr(!!as.symbol(.x) := sum(clinical_code %in% !!.y)))

    diagnoses_and_procedures %>%
        filter(clinical_code_type == "diagnosis") %>%
        group_by({{ record_id }}) %>%
        mutate(!!!count_args)
}
