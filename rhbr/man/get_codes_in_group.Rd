% Generated by roxygen2: do not edit by hand
% Please edit documentation in R/rust_interface.R
\name{get_codes_in_group}
\alias{get_codes_in_group}
\title{Get a dataframe (tibble) of all the docs in a particular group
defined in a codes file.}
\usage{
get_codes_in_group(codes_file_path, group)
}
\description{
The tibble contains two columns:
\itemize{
\item name: for the clinical code name (e.g. "I22.1")
\item docs: for the description of the code (e.g. "Subsequent
myocardial infarction of inferior wall").
}
}
\details{
The group is defined by the codes file (e.g. icd10.yaml), and
code groups can be edited using the codes editor program.
}
