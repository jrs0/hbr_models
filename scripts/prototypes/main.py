# Full model development process
#
# This file contains
#

from models import SimpleLogisticRegression, TruncSvdLogisticRegression
from fit import fit_and_save


def fit_bleeding_ischaemia_models(model_data):
    model_data["outcome"] = "bleeding_al_ani_outcome"
    fit_and_save(model_data)
    model_data["outcome"] = "hussain_ami_stroke_outcome"
    fit_and_save(model_data)


# These are the models that should be fitted on every
# dataset
model_list = [
    SimpleLogisticRegression,
    TruncSVDLogisticRegression,
]

# These are the datasets that should be inputted to
# every model
dataset_specs = [
    # HES-only, manual code groups
    {
        "dataset_name": "manual_codes",
        "sparse_features": False,
    },
    # HES-only, all codes
    {
        "dataset_name": "all_codes",
        "sparse_features": False,
    },
    # HES, manual_codes + SWD
    {
        "dataset_name": "manual_codes_swd",
        "sparse_features": False,
    },
]

# Build all combinations of datasets and models
fit_spec = []
for model in model_list:
    for dataset_spec in dataset_specs:
        fit_spec = {
            "model": model,
            "config_file": "config.yaml"
        } | dataset_spec
        
        
        


# Define the fits that should be performed
fit_specs = [
    # Fit 0: simple logistic regression, HES + SWD
    {
        "dataset_name": "manual_codes_swd",
        "model": SimpleLogisticRegression,
        "sparse_features": False,
        "config_file": "config.yaml",
    },
    # Fit 1: truncated SVD, logistic regression, HES + SWD
    {
        "dataset_name": "manual_codes_swd",
        "model": TruncSvdLogisticRegression,
        "sparse_features": False,
        "config_file": "config.yaml",
    },
    # Simple logistic regression, HES groups,
    {
        "dataset_name": "manual_codes",
        "model": SimpleLogisticRegression,
        "sparse_features": False,
        "config_file": "config.yaml",
    },
]

for model_data in fit_specs:
    fit_bleeding_ischaemia_models(model_data)

# Truncated SVD, HES groups
model_data = {
    "dataset_name": "all_codes",
    "model": TruncSvdLogisticRegression,
    "sparse_features": True,
    "config_file": "config.yaml",
}
fit_bleeding_ischaemia_models(model_data)
