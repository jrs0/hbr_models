##' Prototype calculation of ARC HBR score from HIC dataset

start_time <- Sys.time()

# Set the working directory here
setwd("scripts/prototypes")

library(tidyverse)

# Either load rhic using rextendr::document() (from the rhic/ directory)
# or install rhic and use library(rhic). Pick one of the options from
# below
# library(rhic)
rextendr::document(pkg = "../../rhic")

con <- DBI::dbConnect(odbc::odbc(), "hic", bigint = "character")
id <- dbplyr::in_catalog("HIC_COVID_JS", "dbo", "cv_covid_pathology_blood")

raw_data <- dplyr::tbl(con, id) %>%
    head(50) %>%
    collect()