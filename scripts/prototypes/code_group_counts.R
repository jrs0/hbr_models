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
get_code_list <- function(code_groups, group_name) {
    code_groups %>%
        filter(group == group_name) %>%
        pull(name)
}

##' Get a list of all the code groups of a particular type
##' (either diagnosis or procedure). Returns a list containing
##' two items:
##'
##' - the list of group names
##' - a list  of code lists (each one associated to a group name)
##'
##' Used as a helper in counting instances of code occurances. The
##' purpose of returning data in this format is to make it easy to use
##' pmap directly for iterating over both the group names and the 
##' associated code lists.
get_code_lists <- function(code_groups, group_type) {
    code_group_names <- code_groups %>%
        filter(type == group_type) %>%
        distinct(group) %>%
        pull(group)

    code_lists <- code_group_names %>%
        map(~ get_code_list(code_groups, .x))

    list(
        code_group_names,
        code_lists
    )
}

##' codes_table is a tibble with a column called clinical_code
##' containing the codes, and a record_id which groups the codes
##' together. The function reduces to one row per record id, and
##' a column called count which contains the total clinical_codes
##' matching the code_list.
count_codes_in_group <- function(codes_table, record_id, code_list) {
    codes_table %>%
        mutate(code_match = clinical_code %in% code_list) %>%
        group_by({{ record_id }}) %>%
        summarise("count" := sum(code_match))
}

##' Take a table of diagnoses and procedures, filter to only keep one
##' type (diagnosis or procedure), and then count the occurances of all
##' code groups in the code_groups lists for each record_id. Used as a 
##' helper in the code count function below.
count_codes_by_type <- function(diagnoses_and_procedures, record_id, code_groups, diagnosis_or_procedure) {
    code_groups %>%
        get_code_lists(diagnosis_or_procedure) %>%
        pmap(~ diagnoses_and_procedures %>%
            filter(clinical_code_type == diagnosis_or_procedure) %>%
            count_codes_in_group({{ record_id }}, .y) %>%
            rename(!!paste0(.x, "_count") := count)) %>%
        reduce(left_join, by = join_by({{ record_id }}))
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

    # The steps are as follows: first, iterate over the diagnosis code lists, which are
    # code group names x paired with lists of codes y. For each list y, count the number
    # of diagnosis codes in the clinical_code column, for each record_id, so that you get
    # a dataframe out with the total count for each record id. This total count is given
    # a column name like group_name_count. Reduce by left joining together the counts,
    # which leaves a single table of record_id and one column for each count.
    diagnosis_group_counts <- diagnoses_and_procedures %>%
        count_codes_by_type({{ record_id }}, code_groups, "diagnosis")
    
    # Do the same for procedures
    procedure_group_counts <- diagnoses_and_procedures %>%
        count_codes_by_type({{ record_id }}, code_groups, "procedure")

    # Join the two together to form the full counts table
    diagnosis_group_counts %>%
        left_join(procedure_group_counts, by = join_by({{ record_id }}))
}

