library(tidyverse)
library(corrr)
library(vip)

setwd("scripts/prototypes")
source("save_datasets.R")

raw_data <- load_dataset("raw_data")

# Proportion of index events with a PCI procedure
# (expect the majority)
prop_pci_performed <- raw_data %>%
    pull(idx_pci_performed) %>%
    mean()

# Calculate the proportion of index events with ACS (either
# STEMI or NSTEMI) (expect majority)
prop_mi <- raw_data %>%
    pull(idx_mi) %>%
    mean()

# Calculate proportion of _all_ index events that are STEMI
# or NSTEMI (note some index events are not ACS)
prop_stemi <- raw_data %>%
    pull(idx_stemi) %>%
    mean()
prop_nstemi <- raw_data %>%
    pull(idx_nstemi) %>%
    mean()

# Calculate the proportion of patients with bleeding
# events in one year. Should be around 0-5%. This estimate
# will underestimate risk due to right censoring.
prop_bleed_1y_naive <- raw_data %>%
    pull(outcome_occurred_bleeding_al_ani) %>%
    mean()
