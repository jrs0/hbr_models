# Full model development process
#
# This file contains
#

from fit import fit_model_bootstraps_and_save, SimpleLogisticRegression

model_data = {
    "dataset_name": "hes_code_groups_dataset",
    "model": SimpleLogisticRegression,
    "sparse_features": False,
    "outcome": "bleeding_al_ani_outcome",
    "config_file": "config.yaml",
}

fit_model_bootstraps_and_save(model_data)