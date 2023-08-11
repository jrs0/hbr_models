# Requires library(tidyverse)


##' Find the time to a particular outcome after the index spell
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
find_subsequent_outcome <- function(
    records_after,
    record_idx_id,
    time_to_outcome,
    idx_date,
    outcome_name,
    right_censor_date) {
    outcome_time <- paste0(outcome_name, "_time")
    outcome_status <- paste0(outcome_name, "_status")
    outcome_count <- as.symbol(paste0(outcome_name, "_count"))

    # Find the episodes with a bleeding event and add
    # the survival time and status columns
    idx_with_subsequent_outcome <- records_after %>%
        # Keep only records where the outcome is present.
        filter(!!outcome_count > 0) %>%
        # For each index event, record the time to the
        # first subsequent outcome
        group_by({{ record_idx_id }}) %>%
        summarise(
            !!outcome_time := min({{ time_to_outcome }}),
            !!outcome_status := 1,
        )

    idx_no_subsequent_outcome <- records_after %>%
        # Pick out the index events without a subsequent outcome
        group_by({{ record_idx_id }}) %>%
        filter(all(!!outcome_count == 0)) %>%
        
        #filter(!({{ record_idx_id }} %in% idx_with_bleeding_after$idx_episode_id)) %>%
        transmute(
            {{ record_idx_id }},
            !!outcome_time := right_censor_date - {{ idx_date }}, # Right-censored
            !!outcome_status := 0
        )

    # Join together the bleed/no-bleed rows to get all the bleeding
    # survival data
    index_no_subsequent_outcome %>%
        bind_rows(index_with_subsequent_outcome)
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
