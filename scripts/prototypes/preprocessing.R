# Requires library(tidyverse)


##' Find the time to a particular outcome after the index spell
##'
##' @param records_after The index event and all records after the
##' index event. 
##' @param record_id The id column for rows in records_after. Each
##' row corresponds to a record (either the index record or a subsequent
##' event).
##' @param idx_record_id The column in records_after which is the
##' index id. The index row is identified by record_id == idx_record_id.
##' @param time_to_outcome The column containing the time to the current
##' record from the index record. 
##' @param idx_date The column containing the date of the index event
##' (a function of idx_record_id, not record_id)
##' @param outcome_name The name of the outcome to look for, as a string.
##' There should be a column called outcome_name_count in the records_after
##' table.
##' @param right_censor_date The date used as the right censor when the 
##' outcome is not found in the records after the index event.
##'
##' The spell_time_differences_and_counts is a table of all the
##' spells for a particular patient that occurred after the index
##' event. It contains the spell_time_difference column, which is
##' the time from the index to the other spell.
##'
##' It also contains the outcome_count column, which is formed from
##' the outcome_name by appending "_count". This is the number of
##' occurrences of that outcome in the other spell.
##'
##' The resulting dataframe contains one row per index event, with three
##' columns in total. The function records, for each index spell, two
## pieces of information:
##'
##' - the outcome_time, which is the time to the first occurrence of
##'   the outcome in a subsequent spell. If the outcome did not occur,
##'   then this column contains the time to the right_censor_date, which
##'   is the end date of the data availability window.
##' - the outcome_status, which is a 1 if the outcome occurred, or zero
##'   if it did not occur in a subsequent spell
##'
##' The columns are named according to the outcome_name field, with
##' "_time" and "_status" appended.
##'
find_subsequent_outcome <- function(
    records_after,
    record_id,
    idx_record_id,
    time_to_outcome,
    idx_date,
    outcome_name,
    right_censor_date) {

    outcome_time <- paste0(outcome_name, "_time")
    outcome_status <- paste0(outcome_name, "_status")
    outcome_count <- as.symbol(paste0(outcome_name, "_count"))

    # Find the episodes with a bleeding event and add
    # the survival time and status columns
    idx_with_outcome_after <- records_after %>%
        # Keep only subsequent outcome events. It is important to
        # exclude the index events here, otherwise they may contribute
        # to the count if they contain the outcome.
        filter(!!outcome_count > 0, {{ idx_record_id }} != {{ record_id }}) %>%
        # For each index event, record the time to the first
        # bleeding event.
        group_by({{ idx_record_id }}) %>%
        summarise(
            !!outcome_time := min({{ time_to_outcome }}),
            !!outcome_status := 1,
        )

    idx_no_outcome_after <- records_after %>%
        # Keep the index row and any rows with the subsequent outcome.
        filter((!!outcome_count != 0) |
            ({{ idx_record_id }} == {{ record_id }})) %>%
        group_by(idx_episode_id) %>%
        # The test for whether there is no subsequent outcome is if the group
        # size is exactly one (just index event)
        filter(n() == 1) %>%
        transmute(
            {{ idx_record_id }},
            !!outcome_time := right_censor_date - {{ idx_date }}, # Right-censored
            !!outcome_status := 0
        )

    # Join together the bleed/no-bleed rows to get all the bleeding
    # survival data
    idx_with_outcome_after %>%
        bind_rows(idx_no_outcome_after)
}

##' Adds a column for whether the outcome occurred at 12 months, using
##' the survival time and status columns. The new column is 1 if the
##' status is 1 for survival time less than 12 months; 0 otherwise.
##'
add_12m_outcome <- function(index_with_subsequent_outcome, outcome_name) {
    twelve_months <- lubridate::dyears(1)

    outcome_time <- as.symbol(paste0(outcome_name, "_time"))
    outcome_status <- as.symbol(paste0(outcome_name, "_status"))
    outcome_12m <- paste0(outcome_name, "_12m")

    index_with_subsequent_outcome %>%
        mutate(!!outcome_12m := if_else(
            (!!outcome_time < twelve_months) & (!!outcome_status == 1),
            1,
            0
        ))
}
