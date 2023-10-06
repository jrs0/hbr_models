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


# Simple logistic regression, HES groups,
model_data = {
    "dataset_name": "hes_code_groups_dataset",
    "model": SimpleLogisticRegression,
    "sparse_features": False,
    "config_file": "config.yaml",
}
fit_bleeding_ischaemia_models(model_data)

# Truncated SVD, HES groups
model_data = {
    "dataset_name": "hes_all_codes_dataset",
    "model": TruncSvdLogisticRegression,
    "sparse_features": True,
    "config_file": "config.yaml",
}
fit_bleeding_ischaemia_models(model_data)
