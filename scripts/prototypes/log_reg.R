library(tidyverse)
library(tidymodels)
library(corrr)
library(vip)

setwd("scripts/prototypes")

source("save_datasets.R")

raw_data <- load_dataset("hes_spells_dataset") %>%
    # Drop variables that are not used here
    select(-idx_date, -matches("(time|status)"))

# Check correlations with bleeding outcome
raw_data %>%
    correlate() %>%
    focus(outcome_12m_bleeding_al_ani) %>%
    arrange(desc(outcome_12m_bleeding_al_ani))

# Process the dataset for modelling
dataset <- raw_data %>%
    mutate(across(where(is.character), as.factor)) %>%
    mutate(across(where(is.logical), as.factor)) %>%
    # These are defects in the dataset -- should be fixed
    # at source
    drop_na() %>%
    mutate(outcome_12m_bleeding_al_ani = factor(outcome_12m_bleeding_al_ani,
        levels = c("1", "0")))

# Check proportion of bleeding outcome
dataset %>%
    count(outcome_12m_bleeding_al_ani) %>%
    mutate(prop = n / sum(n))

set.seed(1)
splits <- initial_split(dataset, strata = outcome_12m_bleeding_al_ani)
dataset_other <- training(splits)
dataset_test <- testing(splits)

val_set <- validation_split(dataset_other,
    strata = outcome_12m_bleeding_al_ani,
    prop = 0.80
)

lr_mod <-
    logistic_reg(penalty = tune(), mixture = 1) %>%
    set_engine("glmnet")

lr_recipe <-
    recipe(outcome_12m_bleeding_al_ani ~ ., data = dataset_other) %>%
    step_rm(outcome_12m_mi_schnier) %>%
    step_dummy(all_nominal_predictors()) %>%
    step_zv(all_predictors()) %>%
    step_impute_mean(idx_age) %>%
    step_normalize(all_numeric_predictors())

lr_workflow <-
    workflow() %>%
    add_model(lr_mod) %>%
    add_recipe(lr_recipe)

# Grid of penalties to try
lr_reg_grid <- tibble(penalty = 10^seq(-4, -1, length.out = 30))

lr_res <-
    lr_workflow %>%
    tune_grid(val_set,
        grid = lr_reg_grid,
        control = control_grid(save_pred = TRUE),
        metrics = metric_set(roc_auc)
    )

lr_plot <-
    lr_res %>%
    collect_metrics() %>%
    ggplot(aes(x = penalty, y = mean)) +
    geom_point() +
    geom_line() +
    ylab("Area under the ROC Curve") +
    scale_x_log10(labels = scales::label_number())

lr_plot

top_models <-
  lr_res %>% 
  show_best("roc_auc", n = 15) %>% 
  arrange(penalty) 
top_models

lr_best <- 
  lr_res %>% 
  collect_metrics() %>% 
  arrange(penalty) %>% 
  slice(12)
lr_best

lr_auc <- 
  lr_res %>% 
  collect_predictions(parameters = lr_best) %>% 
  roc_curve(outcome_12m_bleeding_al_ani, .pred_1) %>% 
  mutate(model = "Logistic Regression")

autoplot(lr_auc)

####### GET THE BEST MODEL BY ROC AUC #######

lr_best <- lr_res %>%
    select_best("roc_auc")

final_workflow <- lr_workflow %>%
    finalize_workflow(lr_best)

final_fit <- final_workflow %>%
    last_fit(splits)

# Show the final accuracy and AUC (and other metrics)
final_fit %>%
    collect_metrics()

final_model_spec <- final_fit %>%
    extract_fit_parsnip()

# Show the importance of the predictors
final_model_spec %>%
    vip(num_features = 20)

# Get the actual model -- maybe gets the coefficients?
final_model <- final_fit %>%
    extract_fit_engine() %>%
    coef()