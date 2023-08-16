library(tidyverse)
library(corrr)
library(vip)
library(ggplot2)

setwd("scripts/prototypes")
source("save_datasets.R")


raw_data <- load_dataset("hes_spells_dataset")

# Proportion of index events with a PCI procedure
# (expect a large proportion).
prop_pci_performed <- raw_data %>%
    pull(pred_idx_pci_performed) %>%
    mean()

# Proportion of index events that are ACS events
# (expect the majority) -- some index event may contain
# a PCI without having an ACS.
prop_acs <- raw_data %>%
    pull(pred_idx_acs) %>%
    mean()

# Calculate proportion of ACS events that are STEMI or
# NSTEMI
prop_stemi <- raw_data %>%
    filter(pred_idx_acs) %>%
    pull(pred_idx_stemi) %>%
    mean()
prop_nstemi <- raw_data %>%
    filter(pred_idx_acs) %>%
    pull(pred_idx_nstemi) %>%
    mean()

# Calculate the proportion of patients with bleeding
# events in one year. Should be around 0-5%. This estimate
# will underestimate risk due to right censoring.
prop_bleed_1y_naive <- raw_data %>%
    filter(!is.na(outcome_occurred_bleeding_al_ani)) %>%
    pull(outcome_occurred_bleeding_al_ani) %>%
    mean()

# Plot the distribution of age in the dataset
raw_data %>%
    ggplot(aes(x = pred_idx_age)) +
    geom_histogram(binwidth=5) +
    labs(title = "Distribution of ages at index",
    x = "Age", y = "")

# Plot correlations between properties of the index
x <- raw_data %>%
    select(matches("(pred|outcome)")) %>%
    filter(!is.na(outcome_occurred_bleeding_al_ani)) %>%
    correlate() %>%
    focus(outcome_occurred_bleeding_al_ani)
    
    rearrange() %>%
    shave()

fashion(x)
rplot(x)

raw_data %>%
    pivot_longer(matches("pred_idx")) %>%
    colnames()
    
    
        ggplot(aes(x = matches("pred_idx"))) +
    geom_bar(stat="count")