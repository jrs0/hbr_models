# Full model development process
#
# This file contains 
#

import os
os.chdir("scripts/prototypes")

from stability import make_bootstrapped_resamples
from fit import fit_logistic_regression

from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

import importlib

## To be deleted
import stability, fit
importlib.reload(stability)
importlib.reload(fit)


# Example data for now
X, y = make_classification(
    n_samples=100_000, n_features=20, n_informative=2, n_redundant=2, random_state=42
)

train_samples = 100  # Samples used for training the models
X0_train, X_test, y0_train, y_test = train_test_split(  
    X,
    y,
    shuffle=False,
    test_size=100_000 - train_samples,
)

# Develop a single model from the training set (X0_train, y0_train),
# using any method (e.g. including cross validation and hyperparameter
# tuning) using training set data. This is referred to as D in 
# stability.py.
M0 = fit_logistic_regression(X0_train, y0_train)

# For the purpose of assessing model stability, obtain bootstrap
# resamples (Xn_train, yn_train) from the training set.
Xn_train, yn_train = make_bootstrapped_resamples(X0_train, y0_train, N = 200)

# Develop all the bootstrap models to compare with the model-under-test M0
Mn = [fit_logistic_regression(X, y) for (X, y) in zip(Xn_train, yn_train)]

