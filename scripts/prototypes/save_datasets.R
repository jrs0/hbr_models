##' Get the current git commit hash (first 12 chars only)
current_commit <- function() {
    # Get the current commit in the repository
    hash <- system("git rev-parse HEAD", intern = TRUE)
    stringr::str_extract(hash, "^.{12}")
}

##' Get the current time as a unix timestamp
timestamp_now <- function() {
    as.integer(Sys.time())
}

##' Write a dataset to a file in the datasets/ directory
##' (assumes that the current working directory is set
##' correctly)
##'
##' The filename should be in the form "dataset_name" (no
##' file extension). The name will have the current commit
##' and the current timestamp appended, as well as .rds
##'
##' Read the dataset using load_dataset()
save_dataset <- function(dataset, name) {
    # Write the dataset to a file
    datasets_dir <- "datasets" # No trailing /

    # Make the file suffix out of the current git
    # commit hash and the current time
    suffix <- paste(current_commit(), timestamp_now(), sep = "_")
    full_filename <- paste0(datasets_dir, "/", name, "_", suffix, ".rds")

    if (!fs::dir_exists(datasets_dir)) {
        message("Creating missing folder", datasets_dir, "/ for storing dataset")
        fs::dir_create(datasets_dir)
    }
    saveRDS(dataset, full_filename)
}

##' Read a dataset from the datasets/ folder
##'
##' The filename is used to search for files of the
##' form datasets/filename_commit_timestamp.rds. If
##' multiple files match the filename, then the one
##' with the latest timestamp is chosen.
load_dataset <- function(name) {
    # Check for missing datasets directory
    datasets_dir <- "datasets" # No trailing /
    if (!fs::dir_exists(datasets_dir)) {
        stop("Missing folder", datasets_dir, ". Check your working directory")
    }

    # Pattern to match name part and file extension
    pattern <- paste0("(\\.rds|", name, "_)")

    latest_filename <- tibble::tibble(file = list.files(datasets_dir)) %>%
        # First, filter by the filename and then drop the filename
        filter(str_detect(file, name)) %>%
        mutate(commit_and_timestamp = str_replace(file, pattern, "")) %>%
        separate_wider_delim(commit_and_timestamp,
            delim = "_",
            names = c("commit", "timestamp")
        ) %>%
        arrange(desc(timestamp)) %>%
        head(1) %>%
        pull(file)

    if (length(latest_filename) == 0) {
        stop(
            "Did not find a dataset called ", name,
            ". Did you spell it correctly?"
        )
    }

    readRDS(paste0(datasets_dir, "/", latest_filename))
}
