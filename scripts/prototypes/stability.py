# Assessing model stability
#
# Model stability of an internally-validated model
# refers to how well models developed on a similar internal
# population agree with each other. The methodology for
# assessing model stability follows Riley and Collins, 2022 
# (https://arxiv.org/abs/2211.01061)
#
# Assessing model stability is an end-to-end test of the entire
# model development process. Riley and Collins do not refer to
# a test/train split, but their method will be interpreted as
# applying to the training set (with instability measures assessed
# by applying models to the test set). As a result, the first step
# in the process is to split the internal dataset into a training
# set P0 and a test set T.
#
# Assuming that a training set P0 is used to develop a model M0 
# using a model development  process D (involving steps such 
# cross-validation and hyperparameter tuning in the training set, 
# and validation of accuracy of model prediction in the test set), 
# the following steps are required to assess the stability of M0:
#
# 1. Bootstrap resample P0 with replacement M >= 200 times, creating 
#    M new datasets Pm that are all the same size as P0
# 2. Apply D to each Pm, to obtain M new models Mn which are all
#    comparable with M0.
# 3. Collect together the predictions from all Mn and compare them
#    to the predictions from M0 for each sample in the test set T.
# 4. From the data in 3, plot instability plots such as a scatter
#    plot of M0 predictions on the x-axis and all the Mn predictions
#    on the y-axis, for each sample of T. In addition, plot graphs
#    of how all the model validation metrics vary as a function of
#    the bootstrapped models Mn.
#
# Implementation
#
# A function is required that takes the original training set P0
# and generates N bootstrapped resamples Pn that are the same size
# as P.
#
# A function is required that wraps the entire model
# into one call, taking as input the bootstrapped resample Pn and
# providing as output the bootstrapped model Mn. This function can
# then be called N times to generate the bootstrapped models. This
# function is not defined in this file (see the fit.py file)
#
# An aggregating function will then take all the models Mn, the 
# model-under-test M0, and the test set T, and make predictions
# using all the models for each sample in the test set. It should
# return all these predictions (probabilities) in a 2D array, where
# each row corresponds to a test-set sample, column 0 is the probability
# from M0, and columns 1 through M are the probabilities from each Mn.
#
# This 2D array may be used as the basis of instability plots. Paired
# with information about the true outcomes y_test, this can also be used
# to plot ROC-curve variability (i.e. plotting the ROC curve for all
# model M0 and Mn on one graph). Any other accuracy metric of interest
# can be calculated from this information (i.e. for step 4 above).

import numpy as np
from sklearn.utils import resample

def make_bootstrapped_resamples(X0_train, y0_train, N):
    '''
    Makes N boostrapped resamples of P0 that are the same
    size as P0. N must be at least 200 (as per recommendation).
    P0 is specified by its features X0_train and its outcome
    y0_train, which must both be the same height (same number
    of rows). 

    Note: not yet reproducible from random_state.

    Testing: not yet tested.
    '''
    num_samples = X0_train.shape[0]
    if num_samples != len(y0_train):
        raise ValueError("Number of rows in X0_train and y0_train must match")
    if N < 200:
        raise ValueError("N must be at least 200; see Riley and Collins, 2022")
    
    Xn_train = []
    yn_train = []
    for i in range(N):
        X, y = resample(X0_train, y0_train)
        Xn_train.append(X)
        yn_train.append(y)

    return Xn_train, yn_train

def predict_bootstrapped_proba(M0, Mn, X_test):
    '''
    Aggregating function which finds the predicted probability
    from the model-under-test M0 and all the bootstrapped models
    Mn on each sample of the training set features X_test. The
    result is a 2D numpy array, where each row corresponds to
    a test-set sample, the first column is the predicted probabilities
    from M0, and the following N columns are the predictions from all
    the other Mn.

    Note: the numbers in the matrix are the probabilities of 1 in the
    test set y_test.

    Testing: not yet tested
    '''
    columns = []
    for M in [M0] + Mn:
        columns.append(M.predict_proba(X_test)[:,1])
    
    return np.column_stack(columns)

