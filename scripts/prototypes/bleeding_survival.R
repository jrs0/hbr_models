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

# Set the working directory here
setwd("scripts/prototypes")

library(tidyverse)
source("save_datasets.R")

raw_data <- load_dataset("hic_episodes_dataset")

dataset <- raw_data %>%
    mutate(
        time = outcome_time_bleeding_al_ani,
        status = outcome_status_bleeding_al_ani
    ) %>%
    select(
        matches("idx"),
        matches("before"),
        time,
        status
    )


####### SURVIVAL ANALYSIS (OVERALL) #######

library(survival)
library(ggsurvfit)
library(gtsummary)

sv <- Surv(dataset$time, dataset$status)
s1 <- survfit(Surv(time, status) ~ 1, data = dataset)

# Plot Kaplan-Meier curves
survfit2(Surv(time, status) ~ 1, data = dataset) %>%
    ggsurvfit() +
    # Convert x scale to days
    scale_x_continuous(labels = function(x) x / 86400) +
    labs(x = "Days", y = "Overall survival probability") +
    add_confidence_interval() +
    add_risktable()

# Find the bleeding risk at one year. This shows the survival
# probability at one year, along with upper and lower confidence
# intervals.
one_year_risk <- summary(survfit(Surv(time, status) ~ 1, data = dataset),
    times = 365 * 24 * 60 * 60
)

# Get one year risk of bleed
p_bleed_1y <- 1 - one_year_risk$surv

# Upper and lower CI are swapped (because they are survival)
p_bleed_one_year_upper <- 1 - one_year_risk$lower # Lower CI, 95%
p_bleed_one_year_lower <- 1 - one_year_risk$upper # Upper CI, 95%

# Show survival in table
survfit(Surv(time, status) ~ 1, data = dataset) %>%
    tbl_survfit(
        times = 365 * 24 * 60 * 60,
        label_header = "**1-year survival (95% CI)**"
    )

####### SURVIVAL ANALYSIS (AGE INPUT) #######

coxph(Surv(time, status) 
    ~ idx_stemi + idx_nstemi + idx_pci_performed + idx_mi,
    data = dataset)

survdiff(Surv(bleeding_time, bleeding_status) ~ age_at_index,
    data = dataset
)

# Show the regression results as a table
coxph(
    Surv(time, status)
        ~ idx_stemi + idx_nstemi + idx_pci_performed + idx_mi,
    data = dataset
) %>%
    tbl_regression(exp = TRUE)
