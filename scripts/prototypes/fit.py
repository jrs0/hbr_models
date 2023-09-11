# Model fitting function
#
# This file contains the process referred to in
# stability.py as D, which takes as input a training
# set (X, y), and outputs a scikit-learn pipeline. 
#
# The feature matrix X is a numerical array where
# columns are predictors (features) and rows are
# samples corresponding to an outcome in the vector
# y. As far as possible, X should be preprocessed
# before handing it over to this function. However,
# this preprocessing must _not_ include any information
# from the testing set. More generally, we only allow 
# preprocessing that applies an operation to each 
# sample of the dataset that is:
# 
# - local, meaning it only involves values from the
#   given row of X.
# - determinstic, meaning it does not involve any
#   elements of randomness.
# - non-parametrised, meaning the preprocessing does
#   not depend on parameters which may need to be 
#   tuned over.
#
# These conditions are stronger than required to
# prevent leakage of test data into training data,
# but are designed to push non-trivial preprocessing
# into the model development pipeline where it can
# be tuned and consistently applied to training and
# testing data.
# 
# Examples of preprocessing that can be performed on
# X before passing it to the fit functions:
#
# - Creating a feature by counting the number of 
#   diagnosis codes before the index event. This
#   is a local (to the index event) operation 
#   which is non-parametric and deterministic.
# - Creating features which are deterministic 
#   functions of the index event (for example, whether
#   the index MI is STEMI or NSTEMI).
# 
# Examples of preprocessing that must not be performed
# on X before passing it to the fit functions

#
# - Any imputing of data which involves a global 
#   computation (such as imputing an age column based
#   on the mean)
# - Any dimension reduction (such as UMAP) that depends
#   on tuning parameters and is also a global operation.
# - Any centering and scaling, which is a global operation.
#

from sklearn.linear_model import LogisticRegression

def fit_logistic_regression(X_train, y_train):
    '''
    Example fitting function (in this case LR).
    Stand-in for a more complicated function that
    performs cross-validation, hyperparameter tuning
    etc. This kind of function is clearly model 
    specific, so there is going to be a function like
    this for each model. However, all of them have to
    output a fitted object. In addition, they may want
    to output addition information specific to that model,
    (such as hyperparameter tuning results), so we may
    want to output a class eventually.

    Testing: not yet tested
    '''
    m = LogisticRegression(max_iter=1000)
    m.fit(X_train, y_train) 
    return m