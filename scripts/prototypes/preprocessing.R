# Requires library(tidyverse)

##' Find the time to a set of outcomes from a table of index and
##' subsequent records.
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
##' @param outcomes A list of the names of the outcome to look for, as a
##' character vector. For each item outcome in the list, there should be a
##' column called outcome_count in the records_after table.
##' @param right_censor_date The date used as the right censor when the
##' outcome is not found in the records after the index event.
##' @param follow_up The time at which to calculate a fixed outcome
##' occurred/did-not-occur flag.
##'
##' The resulting dataframe contains one row per index event, and three
##' columns per outcome:
##' - the outcome_time, which is the time to the first occurrence of
##'   the outcome in a subsequent spell. If the outcome did not occur,
##'   then this column contains the time to the right_censor_date, which
##'   is the end date of the data availability window.
##' - the outcome_status, which is a 1 if the outcome occurred, or zero
##'   if it did not occur in a subsequent spell
##' - the outcome_occurred, which is 1 if the outcome occurred before
##'   the follow_up time, zero if it did not, or NA if it is not possible
##'   to tell from the outcome_time and outcome_status columns.
##'
##' The columns are named according to the outcome_name field, with
##' "_time" and "_status" appended.
##'
add_outcome_columns <- function(
    records_after,
    record_id,
    idx_record_id,
    time_to_outcome,
    idx_date,
    outcomes,
    right_censor_date,
    follow_up) {

    # For each outcome, calculate the three new outcome
    # columns and join all the results together by idx_record_id.
    outcomes %>%
        map(
            ~ records_after %>%
                find_subsequent_outcome(
                    {{ record_id }},
                    {{ idx_record_id }},
                    {{ time_to_outcome }},
                    {{ idx_date }},
                    .x,
                    right_censor_date
                ) %>%
                add_fixed_follow_up_outcome(.x, follow_up)
        ) %>%
        # The result of the map above is a list of tibbles,
        # one per outcome, which share only the idx_record_id
        # column in common. It is therefore possible to left
        # join them all together based on this key.
        reduce(left_join)
}

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
##' @param outcome The name of the outcome to look for, as a string.
##' There should be a column called outcome_count in the records_after
##' table.
##' @param right_censor_date The date used as the right censor when the
##' outcome is not found in the records after the index event.
##'
##' The resulting dataframe contains one row per index event, with three
##' columns in total. The function records, for each index spell, two
##  pieces of information:
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
    outcome,
    right_censor_date) {
    outcome_time <- paste0(outcome, "_time")
    outcome_status <- paste0(outcome, "_status")
    outcome_count <- as.symbol(paste0(outcome, "_count"))

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
        group_by({{ idx_record_id }}) %>%
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

##' Adds a column for whether the outcome occurred at before a fixed
##' follow-up period expired.
##'
##' @param idx_records_with_outcome An input tibble where each
##' row is an index event with information about whether the outcome
##' occurred or not (outcome_status) and the time to the outcome
##' (outcome_time), which is interpreted as a right-censored date if
##' the outcome did not occur.
##' @param outcome The name of the outcome column (a string). Used to
##' generate the real column names (outcome_status and outcome_time).
##' @param follow_up The time at which to compute whether the outcome
##' occurred or not.
##'
##' The function appends a new column to the tibble with the name
##' outcome_occurred. The column may contain NA, in the case when the
##' outcome was not observed, but the right-censored time is before
##' the follow-up time (meaning that it is unknown whether the outcome
##' occurred or not).
##'
##'
add_fixed_follow_up_outcome <- function(idx_records_with_outcome, outcome, follow_up) {
    outcome_time <- as.symbol(paste0(outcome, "_time"))
    outcome_status <- as.symbol(paste0(outcome, "_status"))
    outcome_occurred <- paste0(outcome, "_occurred")

    idx_records_with_outcome %>%
        mutate(!!outcome_occurred := case_when(
            # If the outcome first occurred after the follow-up period,
            # then it did not occur before.
            (!!outcome_status == 1) & (!!outcome_time > follow_up) ~ 0,
            # This is the case when the outcome definitely occurred
            # before the follow-up time
            (!!outcome_status == 1) & (!!outcome_time <= follow_up) ~ 1,
            # In this case, the outcome did not occur, and the right-censor
            # date means that it is known the outcome did not occur until
            # at least after the follow-up date
            (!!outcome_status == 0) & (!!outcome_time > follow_up) ~ 0,
            # If the outcome did not occur, but the right-censor date
            # is before the follow-up, then it is unknown whether
            # the outcome occurred by follow-up or not
            TRUE ~ NA,
        ))
}
