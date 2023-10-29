# Full model development process
#
# This file contains the main fitting process. Run the file to fit
# a set of models to a set of datasets in the datasets/ directory. The
# resulting models are saved to the models/ directory.
#

from models import (
    SimpleLogisticRegression,
    TruncSvdLogisticRegression,
    SimpleDecisionTree,
    TruncSvdDecisionTree,
    SimpleRandomForest,
    SimpleLinearSvc,
    SimpleNaiveBayes,
    SimpleGradientBoostedTree,
    SimpleNeuralNetwork,
)
from fit import fit_and_save
import time

# Record the time taken to run this script
start = time.time()

# Either run all combinations of models and datasets (True),
# or run for a specific model and dataset (False) by picking the model
# and dataset index in the lists below
run_all_models = True
model_choice = 2
dataset_choice = 1

# These are the models that should be fitted on every
# dataset
model_list = [
    SimpleNeuralNetwork, # 0
    SimpleGradientBoostedTree, # 1
    SimpleNaiveBayes, # 2
    SimpleRandomForest, # 3
    TruncSvdDecisionTree, # 4
    SimpleLogisticRegression,  # 5
    TruncSvdLogisticRegression,  # 6
    SimpleDecisionTree,  # 7
    #SimpleLinearSvc, # 0
]

# These are the datasets that should be inputted to
# every model
dataset_specs = [
    # 0: HES-only, manual code groups
    {
        "dataset_name": "manual_codes",
        "sparse_features": False,
    },
    # 1: HES, manual_codes + SWD
    {
        "dataset_name": "manual_codes_swd",
        "sparse_features": False,
    },
    # 2: HES-only, all codes
    {
        "dataset_name": "all_codes",
        "sparse_features": True,
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
    # (model_choice, dataset_choice, reason)
    (5, 2): "dataset too big for simple logistic regression",
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
        print(
            f"Warning, requested fit is excluded: {exclusions[(model_choice, dataset_choice)]}"
        )
    fit_spec = make_fit_spec(model_list[model_choice], dataset_specs[dataset_choice])
    fit_bleeding_ischaemia_models(fit_spec)
else:
    for model_choice, model in enumerate(model_list):
        for dataset_choice, dataset_spec in enumerate(dataset_specs):
            print(f"Starting training for {model.name()} on {dataset_spec['dataset_name']}")
            if (model_choice, dataset_choice) in exclusions.keys():
                print(
                    f"Skipping fit due to: {exclusions[(model_choice, dataset_choice)]}"
                )
            else:
                fit_spec = make_fit_spec(model, dataset_spec)
                fit_bleeding_ischaemia_models(fit_spec)
            print(f"Finished training for {model} on {dataset_spec['dataset_name']}")


# Print the runtime
stop = time.time()
print(f"Time to fit model(s): {stop - start}")
