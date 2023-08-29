# Helper to calculate prevalence of ARC HBR columns
arc_hbr_prevalence <- function(dataset, arc_hbr_column) {
    dataset %>%
        mutate(nonzero = ({{ arc_hbr_column }} != 0)) %>%
        pull(nonzero) %>%
        mean()
}

##' Calculate the prevalence of various ARC HBR criteria,
##' vs. the numbers in 2019, Urban.
##'
arc_hbr_prevalence_summary <- function(dataset) {
    # Expect about 30%
    prev_ckd <- dataset %>%
        arc_hbr_prevalence(pred_arc_hbr_ckd)

    # Expect about 22%
    prev_anaemia <- dataset %>%
        arc_hbr_prevalence(pred_arc_hbr_anaemia)

    # Expect about 1.5% - 2.5%
    prev_tcp <- dataset %>%
        arc_hbr_prevalence(pred_arc_hbr_tcp)

    # Expect about ?
    prev_oac <- dataset %>%
        arc_hbr_prevalence(pred_arc_hbr_oac)

    #  Expect about ?
    prev_age <- dataset %>%
        arc_hbr_prevalence(pred_arc_hbr_age)

    # Collect into a table
    prevalence <- tibble::tibble(
        criterion = c("age", "oac", "ckd", "anaemia", "tcp"),
        hic = 100 * c(prev_age, prev_oac, prev_ckd, prev_anaemia, prev_tcp),
        hbr_paper = c(NA, NA, 30, 21.6, 2.5)
    )
}
