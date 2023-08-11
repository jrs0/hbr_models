library(tidyverse)
library(tidymodels)
library(corrr)
library(vip)

setwd("scripts/prototypes")
source("save_datasets.R")

raw_data <- load_dataset("hic_episodes_dataset") %>%
    # Drop variables that are not used here
    select(-idx_date, -matches("(time|status)"))

# Check correlations with bleeding outcome
raw_data %>%
    correlate() %>%
    focus(outcome_occurred_bleeding_al_ani) %>%
    arrange(desc(outcome_occurred_bleeding_al_ani))

# Process the dataset for modelling
dataset <- raw_data %>%
    mutate(across(where(is.character), as.factor)) %>%
    mutate(across(where(is.logical), as.factor)) %>%
    # These are defects in the dataset -- should be fixed
    # at source
    mutate(occurred = factor(outcome_occurred_bleeding_al_ani,
        levels = c("1", "0")
    )) %>%
    # Drop the other outcome columns
    select(-matches("outcome")) %>%
    # Drop rows where the outcome is unknown
    filter(!is.na(occurred))

# Check proportion of bleeding outcome
dataset %>%
    count(occurred) %>%
    mutate(prop = n / sum(n))

set.seed(1)
splits <- initial_split(dataset, strata = occurred, prop = 3 / 4)
dataset_train <- training(splits)
dataset_test <- testing(splits)

mod <- logistic_reg() %>%
    set_engine("glm")

rec <- recipe(occurred ~ ., data = dataset_train) %>%
    step_dummy(all_nominal_predictors()) %>%
    step_zv(all_predictors()) %>%
    #step_impute_mean(idx_age) %>%
    step_normalize(all_numeric_predictors())

workflow <-
    workflow() %>%
    add_model(mod) %>%
    add_recipe(rec)

fit <- workflow %>%
    fit(data = dataset_train)

# Print the model coefficients
fit %>% extract_fit_parsnip() %>%
    tidy()

aug <- augment(fit, dataset_test)

# Plot ROC curve
aug %>% 
  roc_curve(truth = occurred, .pred_1) %>% 
  autoplot()
