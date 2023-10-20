# Full model development process
#
# This file contains the main fitting process. Run the file to fit
# a set of models to a set of datasets in the datasets/ directory. The
# resulting models are saved to the models/ directory.
#

from models import SimpleLogisticRegression, TruncSvdLogisticRegression
from fit import fit_and_save

# Either run all combinations of models and datasets (True),
# or run for a specific model and dataset (False) by picking the model
# and dataset index in the lists below
run_all_models = True
model_choice = 0
dataset_choice = 2

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

# Certain combinations of models and datasets do not work for practical
# reasons, for example because the dataset includes too many rows and 
# features and the model does not contain any dimension reduction, resulting
# in infeasible computation time. The excluded combinations are given
# below.
#
# Dataset/model combinations are not excluded due to poor modelling performance.
exclusions = {
    # model_choice, dataset_choice, reason
    (0, 1): "dataset too big for simple logistic regression",
}

def make_fit_spec(model, dataset_spec):
    return {"model": model, "config_file": "config.yaml"} | dataset_spec

def fit_bleeding_ischaemia_models(model_data):
    model_data["outcome"] = "bleeding_al_ani_outcome"
    fit_and_save(model_data)
    model_data["outcome"] = "hussain_ami_stroke_outcome"
    fit_and_save(model_data)

# Either run one specific model, or all models and all datasets
if not run_all_models:
    if (model_choice, dataset_choice) in exclusions.keys():
        print(f"Warning, requested fit is excluded: {exclusions[(model_choice, dataset_choice)]}")
    fit_spec = make_fit_spec(model_list[model_choice], dataset_specs[dataset_choice])
    fit_bleeding_ischaemia_models(fit_spec)
else:
    for model_choice, model in enumerate(model_list):
        for dataset_choice, dataset_spec in enumerate(dataset_specs):
            if (model_choice, dataset_choice) in exclusions.keys():
                print(f"Skipping fit due to: {exclusions[(model_choice, dataset_choice)]}")
            else:
                fit_spec = make_fit_spec(model, dataset_spec)
                fit_bleeding_ischaemia_models(fit_spec)