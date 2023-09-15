# Full model development process
#
# This file contains
#

from stability import (
    fit_model,
    predict_bootstrapped_proba,
    plot_instability,
)
from fit import SimpleLogisticRegression, SimpleDecisionTree
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
import save_datasets as ds

# Example data for now. X is the feature matrix (each column is a feature)
# and y is the classification outcome (1 for event occurred). Both must have
# the same number of rows (the number of samples). Both are numerical,
# (X is floating point and y is integer).
# X, y = make_classification(
#    n_samples=1000, n_features=20, n_informative=2, n_redundant=2, random_state=42
# )

# Get real dataset. The bleeding outcome column is called bleeding_al_ani_outcome
# (becomes y) and the other columns except the *_outcome ones become predictors
dataset = ds.load_dataset_interactive("hes_episodes_dataset")
outcome_column = "bleeding_al_ani_outcome"

# Get the features matrix X, and store the feature names
df = dataset.loc[:, ~dataset.columns.str.contains("outcome")]
feature_names = df.columns
X = df.to_numpy()

# Get the outcome vector y
y = dataset[outcome_column].to_numpy()

# Split (X,y) into a testing set (X_test, y_test), which is not used for
# any model training, and a training set (X0,y0), which is used to develop
# the model. Later, (X0,y0) is resampled to generate M additional training
# sets (Xm,ym) which are used to assess the stability of the developed model
# (see stability.py). All models are tested using the testing set.
train_test_split_seed = 22
test_set_proportion = 0.25
X0_train, X_test, y0_train, y_test = train_test_split(
    X, y, test_size=test_set_proportion, random_state=train_test_split_seed
)

Model = SimpleDecisionTree

# Fit the model-under-test M0 to the training set (X0_train, y0_train), and
# fit M other models to M other bootstrap resamples of (X0_train, y0_train).
M0, Mm = fit_model(Model, X0_train, y0_train, M = 200)

# Plot the model
fig, ax = plt.subplots()
M0.plot(ax, feature_names.to_list())
plt.show()

# First columns is the probability of 1 in y_test from M0; other columns
# are the same for the N bootstrapped models Mn.
probs = predict_bootstrapped_proba(M0, Mm, X_test)

# Plot the basic instability curve
fig, ax = plt.subplots()
plot_instability(ax, probs)
plt.show()

# Get the bootstrapped calibration curves
calibration_curves = get_bootstrapped_calibration(probs, y_test, n_bins=10)

# Plot the calibration-stability plots
fig, ax = plt.subplots(2, 1)
plot_calibration_curves(ax[0], calibration_curves)
# Plot the distribution of predicted probabilities, also
# showing distribution stability (over the bootstrapped models)
# as error bars on each bin height
plot_prediction_distribution(ax[1], probs, n_bins=10)
plt.show()

# Get the bootstrapped ROC curves
roc_curves = get_bootstrapped_roc(probs, y_test)
roc_auc = get_bootstrapped_auc(probs, y_test)

# Plot the ROC-stability curves
fig, ax = plt.subplots()
plot_roc_curves(ax, roc_curves, roc_auc)
plt.show()
