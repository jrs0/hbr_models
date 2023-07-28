## The main (user-level) interface to the rust_hic library is defined
## in this file.
##
##


##' Get the list of valid group names defined in a codes file
get_groups_in_codes_file <- function(codes_file_path) {
    if (!file.exists(codes_file_path)) {
        stop("The codes file '", codes_file_path, "' does not exist")
    }
    rust_get_groups_in_codes_file(codes_file_path)
}

##' Get a dataframe (tibble) of all the docs in a particular group
##' defined in a codes file.
##'
##' The tibble contains two columns: "name", for the clinical code
##' name (e.g. "I22.1"); and "docs, for the description of the code
##' (e.g. "Subsequent myocardial infarction of inferior wall"). 
##' The group is defined by the codes file (e.g. icd10.yaml), and
##' code groups can be edited using the codes editor program. 
##'
get_codes_in_group <- function(codes_file_path, group) {
    # This will also check if the codes file exists
    valid_groups <- rust_get_groups_in_codes_file

    if (!any(group == valid_groups)) {
        stop("code group '", group, "' is not present in codes file '", codes_file_path, "'")
    }

    tibble::as_tibble(rust_get_codes_in_group(codes_file_path, group))
}

