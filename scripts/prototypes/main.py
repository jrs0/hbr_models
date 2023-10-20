# Full model development process
#
# This file contains
#

from models import SimpleLogisticRegression, TruncSvdLogisticRegression
from fit import fit_and_save

# Either run all combinations of models and datasets (True),
# or run for a specific model and dataset (False) by picking the model
# and dataset index in the lists below
run_all_models = False
model_choice = 0
dataset_choice = 0

# These are the models that should be fitted on every
# dataset
model_list = [
    SimpleLogisticRegression,  # 0
    TruncSvdLogisticRegression,  # 1
]

# These are the datasets that should be inputted to
# every model
dataset_specs = [
    # 0: HES-only, manual code groups
    {
        "dataset_name": "manual_codes",
        "sparse_features": False,
    },
    # 1: HES-only, all codes
    {
        "dataset_name": "all_codes",
        "sparse_features": True,
    },
    # 2: HES, manual_codes + SWD
    {
        "dataset_name": "manual_codes_swd",
        "sparse_features": False,
    },
]

def make_fit_spec(model, dataset_spec):
    return {"model": model, "config_file": "config.yaml"} | dataset_spec

def fit_bleeding_ischaemia_models(model_data):
    model_data["outcome"] = "bleeding_al_ani_outcome"
    fit_and_save(model_data)
    model_data["outcome"] = "hussain_ami_stroke_outcome"
    fit_and_save(model_data)

# Either run one specific model, or all models and all datasets
if not run_all_models:
    fit_spec = make_fit_spec(model_list[model_choice], dataset_specs[dataset_choice])
    fit_bleeding_ischaemia_models(fit_spec)
else:
    for model in model_list:
        for dataset_spec in dataset_specs:
            fit_spec = make_fit_spec(model, dataset_spec)
            fit_bleeding_ischaemia_models(fit_spec)