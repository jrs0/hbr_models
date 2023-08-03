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
    spell_time_differences_and_counts,
    index_spell_info,
    outcome_name,
    right_censor_date) {

    # Want two things for survival analysis: time to next bleed if there
    # is a bleed; and maximum follow-up date for right censoring, if there is no bleed.
    max_period_after <- lubridate::dyears(1) # limit outcome to 12 months after (for binary classification)
    min_period_after <- lubridate::dhours(72) # Potentially exclude following 72 hours

    outcome_time <- paste0(outcome_name, "_time")
    outcome_status <- paste0(outcome_name, "_status")
    outcome_count <- as.symbol(paste0(outcome_name, "_count"))

    # Table of just the index spells which have a subsequent outcome in the
    # window defined above. This is generic -- the only bit that depends on the
    # column is the filter and summarise part.
    index_with_subsequent_outcome <- spell_time_differences_and_counts %>%
        # Only keep other spells where the bleeding count is non-zero
        # and the spell occurred in the correct window after the index
        filter(
            spell_time_difference >= min_period_after,
            spell_time_difference < max_period_after,
            !!outcome_count > 0,
        ) %>%
        # Group by the index event and pick the first bleeding event
        group_by(spell_id) %>%
        summarise(
            # Note comment above -- might accidentally include
            # the index (to fix)
            !!outcome_time := min(spell_time_difference),
            !!outcome_status := 1,
        )

    # Now get all the index spells where there was no subsequent bleed,
    # and record the right censoring time based on the end date of the
    # raw dataset
    index_no_subsequent_outcome <- index_spell_info %>%
        filter(!(spell_id %in% (index_with_subsequent_outcome$spell_id))) %>%
        transmute(
            spell_id,
            !!outcome_time := right_censor_date - index_date, # Right-censored
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