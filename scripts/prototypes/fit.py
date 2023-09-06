# Model fitting function
#
# This file contains the process referred to in
# stability.py as D, which takes as input a training
# set (X_train, y_train), and outputs a single fitted
# model (or sklearn pipeline eventually). It may use
# any methods it desires, but must produce an object
# capable of preprocessing/transforming a test set in
# the same way as the training set was transformed.
#
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
    m = LogisticRegression()
    m.fit(X_train, y_train) 
    return m