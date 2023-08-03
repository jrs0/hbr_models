# Prototype script for survival analysis on bleeding and thrombotic events
# following PCI procedures and ACS diagnoses.
#
# Purpose: to use data from the HES spells table (ICD-10 diagnoses
# and OPCS-4 procedures) to obtain time-to-bleed and time-to-ischaemia
# for ACS and PCI patients, in order to estimate the two risks using
# survival analysis
#
# Limitations: spells table is used, not episodes. Spells are obtained
# from episodes by a summarizing process which probably drops some of
# the codes. No attempt is made to use the structure of the episodes
# and spells for any purpose (e.g. primary vs. secondary). Code lists
# may not map exactly to the endpoint of interest (clinically relevant
# bleeding and ischaemia).
#
# Run this script from the directory containing the script source in
# this repository (or ensure the path to icd10.yaml and opcs4.yaml are
# correct).
#



####### END OF DATA PREPROCESSING #######

# At this point, expecting to have a dataframe bleed_times with the following
# columns. (Note: if neither acs_stemi_schnier nor acs_nstemi are true, index did not
# contain an ACS.
#
# General information:
# - index_date: what was the index event start date
# Outcomes:
# - bleed_status: whether a bleed occurred (right-censored)
# - bleed_time: time to bleed if occurred, or time to end_date if no bleed
# Predictors:
# - age_at_index:
# - pci_performed: whether index included PCI procedures
# - acs_stemi_schnier: If index was ACS STEMI
# - acs_nstemi: If index was ACS NSTEMI
#


####### SURVIVAL ANALYSIS (OVERALL) #######

library(survival)
library(ggsurvfit)
library(gtsummary)

sv <- Surv(dataset$bleeding_time, dataset$bleeding_status)
s1 <- survfit(Surv(bleeding_time, bleeding_status) ~ 1, data = dataset)

# Plot Kaplan-Meier curves
survfit2(Surv(bleeding_time, bleeding_status) ~ 1, data = dataset) %>%
    ggsurvfit() +
    # Convert x scale to days
    scale_x_continuous(labels = function(x) x / 86400) +
    labs(x = "Days", y = "Overall survival probability") +
    add_confidence_interval() +
    add_risktable()

# Find the bleeding risk at one year. This shows the survival
# probability at one year, along with upper and lower confidence
# intervals.
one_year_risk <- summary(survfit(Surv(bleeding_time, bleeding_status) ~ 1, data = dataset),
    times = 365 * 24 * 60 * 60
)

# Get one year risk of bleed
p_bleed_1y <- 1 - one_year_risk$surv

# Upper and lower CI are swapped (because they are survival)
p_bleed_one_year_upper <- 1 - one_year_risk$lower # Lower CI, 95%
p_bleed_one_year_lower <- 1 - one_year_risk$upper # Upper CI, 95%

# Show survival in table
survfit(Surv(bleeding_time, bleeding_status) ~ 1, data = dataset) %>%
    tbl_survfit(
        times = 365 * 24 * 60 * 60,
        label_header = "**1-year survival (95% CI)**"
    )

####### SURVIVAL ANALYSIS (AGE INPUT) #######

coxph(Surv(bleeding_time, bleeding_status) ~ age_at_index, data = dataset)

survdiff(Surv(bleeding_time, bleeding_status) ~ age_at_index,
    data = dataset
)

# Show the regression results as a table
coxph(
    Surv(bleeding_time, bleeding_status) ~ age_at_index
        + pci_performed + stemi + nstemi,
    data = dataset
) %>%
    tbl_regression(exp = TRUE)
