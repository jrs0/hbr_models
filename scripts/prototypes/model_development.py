# Full model development process
#
# This file contains
#

import os
os.chdir("scripts/prototypes")

###### To be deleted
import stability, fit, calibration, roc
import importlib
importlib.reload(stability)
importlib.reload(fit)
importlib.reload(calibration)
importlib.reload(roc)
######

from stability import (
    make_bootstrapped_resamples,
    predict_bootstrapped_proba,
    plot_instability,
)
from fit import fit_logistic_regression
from calibration import get_bootstrapped_calibration, plot_calibration_curves, plot_prediction_distribution
from roc import get_bootstrapped_roc, get_bootstrapped_auc, plot_roc_curves

from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

import matplotlib.pyplot as plt



# Example data for now
X, y = make_classification(
    n_samples=1000, n_features=20, n_informative=2, n_redundant=2, random_state=42
)

train_samples = 100  # Samples used for training the models
X0_train, X_test, y0_train, y_test = train_test_split(
    X,
    y,
    shuffle=False,
    test_size=0.25,
)

# Develop a single model from the training set (X0_train, y0_train),
# using any method (e.g. including cross validation and hyperparameter
# tuning) using training set data. This is referred to as D in
# stability.py.
M0 = fit_logistic_regression(X0_train, y0_train)

# For the purpose of assessing model stability, obtain bootstrap
# resamples (Xn_train, yn_train) from the training set.
Xn_train, yn_train = make_bootstrapped_resamples(X0_train, y0_train, N=200)

# Develop all the bootstrap models to compare with the model-under-test M0
Mn = [fit_logistic_regression(X, y) for (X, y) in zip(Xn_train, yn_train)]

# First columns is the probability of 1 in y_test from M0; other columns
# are the same for the N bootstrapped models Mn.
probs = predict_bootstrapped_proba(M0, Mn, X_test)

# Plot the basic instability curve
fig, ax = plt.subplots()
plot_instability(ax, probs)
plt.show()

# Get the bootstrapped calibration curves
calibration_curves = get_bootstrapped_calibration(probs, y_test, n_bins = 10)

# Plot the calibration-stability plots
fig, ax = plt.subplots(2,1)
plot_calibration_curves(ax[0], calibration_curves)
# Plot the distribution of predicted probabilities, also
# showing distribution stability (over the bootstrapped models)
# as error bars on each bin height
plot_prediction_distribution(ax[1], probs, n_bins = 10)
plt.show()

# Get the bootstrapped ROC curves
roc_curves = get_bootstrapped_roc(probs, y_test)
roc_auc = get_bootstrapped_auc(probs, y_test)

# Plot the ROC-stability curves
fig, ax = plt.subplots()
plot_roc_curves(ax, roc_curves, roc_auc)
plt.show()
