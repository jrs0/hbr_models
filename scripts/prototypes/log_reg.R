library(tidyverse)
library(tidymodels)

setwd("scripts/prototypes")

source("save_datasets.R")

hes_spells_dataset <- load_dataset("hes_spells_dataset")
