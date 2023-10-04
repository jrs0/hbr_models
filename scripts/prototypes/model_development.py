# Full model development process
#
# This file contains
#

from stability import (
    fit_model,
    predict_bootstrapped_proba,
    plot_instability,
)
from fit import (
    SimpleLogisticRegression,
    SimpleDecisionTree,
    SimpleGradientBoostedTree,
    UmapLogisticRegression,
    TruncSvdLogisticRegression,
    TruncSvdDecisionTree,
    UmapMultiLayerPerceptron,
    UmapDecisionTree,
    UmapGradientBoostedTree,
    SimpleRandomForest
)
from calibration import (
    get_bootstrapped_calibration,
    plot_calibration_curves,
    plot_prediction_distribution,
)
from roc import get_bootstrapped_roc, get_bootstrapped_auc, plot_roc_curves

from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import save_datasets as ds

from imblearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from imblearn.over_sampling import RandomOverSampler
from imblearn.under_sampling import RandomUnderSampler

from sklearn.decomposition import PCA
from sklearn.decomposition import TruncatedSVD

from sklearn.compose import ColumnTransformer

#dataset = ds.Dataset("hes_all_codes_dataset", "config.yaml")
dataset = ds.Dataset("hes_code_groups_dataset", "config.yaml")
#print(dataset)

# Get the feature matrix X and outcome vector y
X = dataset.get_X()
y = dataset.get_y("bleeding_al_ani_outcome")
#y = dataset.get_y("hussain_ami_stroke_outcome")


feature_groups = dataset.feature_groups()
print(f"Feature groups {feature_groups}")
feature_names = dataset.feature_names

# Split (X,y) into a testing set (X_test, y_test), which is not used for
# any model training, and a training set (X0,y0), which is used to develop
# the model. Later, (X0,y0) is resampled to generate M additional training
# sets (Xm,ym) which are used to assess the stability of the developed model
# (see stability.py). All models are tested using the testing set.
train_test_split_rng = np.random.RandomState(0)
test_set_proportion = 0.25
X0_train, X_test, y0_train, y_test = train_test_split(
    X, y, test_size=test_set_proportion, random_state=train_test_split_rng
)

print(f"Training dataset contains {X0_train.shape[0]} rows")
print(f"Outcome vector has mean {np.mean(y0_train)}")

resampler = []#[("oversample", RandomOverSampler()), ("scaler", StandardScaler())]
reducer = [("reducer", TruncatedSVD())]
scaler = [("scaler", StandardScaler())]

preprocess = resampler + reducer + scaler

Model = SimpleLogisticRegression

# Fit the model-under-test M0 to the training set (X0_train, y0_train), and
# fit M other models to M other bootstrap resamples of (X0_train, y0_train).
M0, Mm = fit_model(Model, preprocess, X0_train, y0_train, M=100)

# Plot the model
# fig, ax = plt.subplots()
# M0.plot(ax, feature_names.to_list())
# plt.show()
print(M0.get_model_parameters(feature_names))

# First columns is the probability of 1 in y_test from M0; other columns
# are the same for the N bootstrapped models Mm.
probs = predict_bootstrapped_proba(M0, Mm, X_test)

# At this point, all you need to save is probs, y_test, and any information
# about the best model fit that you want (i.e. params, preprocessing steps, etc.)
fit_data = {
    "model": "simple_logistic_regression",
    "probs": probs,
    "y_test": y_test,
    "other_data": "anything else you want..."
}

ds.save_fit_info(fit_data, "simple_logistic_regression")

d = fit_data#ds.load_fit_info("simple_logistic_regression")

# Plot the basic instability curve
fig, ax = plt.subplots()
plot_instability(ax, d["probs"])
plt.show()

# Get the bootstrapped calibration curves
calibration_curves = get_bootstrapped_calibration(probs, d["y_test"], n_bins=10)

# Plot the calibration-stability plots
fig, ax = plt.subplots(2, 1)
plot_calibration_curves(ax[0], calibration_curves)
# Plot the distribution of predicted probabilities, also
# showing distribution stability (over the bootstrapped models)
# as error bars on each bin height
plot_prediction_distribution(ax[1], d["probs"], n_bins=10)
plt.show()

# Get the bootstrapped ROC curves
roc_curves = get_bootstrapped_roc(d["probs"], d["y_test"])
roc_auc = get_bootstrapped_auc(d["probs"], d["y_test"])

# Plot the ROC-stability curves
fig, ax = plt.subplots()
plot_roc_curves(ax, roc_curves, roc_auc)
plt.show()
