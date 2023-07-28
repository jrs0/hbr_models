## 

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
    tibble::as_tibble(rust_get_codes_in_group(codes_file_path, group))
}

