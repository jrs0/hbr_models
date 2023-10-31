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
# then be called M times to generate the bootstrapped models. This
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
import warnings
import pandas as pd


def make_bootstrapped_resamples(X0_train, y0_train, M):
    """
    Makes M boostrapped resamples of P0 that are the same
    size as P0. M must be at least 200 (as per recommendation).
    P0 is specified by its features X0_train and its outcome
    y0_train, which must both be the same height (same number
    of rows).

    Note: not yet reproducible from random_state.

    Testing: not yet tested.
    """
    num_samples = X0_train.shape[0]
    if num_samples != len(y0_train):
        raise ValueError("Number of rows in X0_train and y0_train must match")
    if M < 200:
        warnings.warn("M should be at least 200; see Riley and Collins, 2022")

    Xn_train = []
    yn_train = []
    for _ in range(M):
        X, y = resample(X0_train, y0_train)
        Xn_train.append(X)
        yn_train.append(y)

    return Xn_train, yn_train


def predict_bootstrapped_proba(M0, Mn, X_test):
    """
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
    """
    columns = []
    for m, M in enumerate([M0] + Mn):
        print(f"Predicting test-set probabilities {m}")
        columns.append(M.model().predict_proba(X_test)[:, 1])

    return np.column_stack(columns)

def smape(A, F):
    terms = []
    for a, f in zip(A, F):
        if a == f == 0:
            terms.append(0)
        else:
            terms.append(2 * np.abs(f - a) / (np.abs(a) + np.abs(f)))
    return (100/len(A)) * np.sum(terms)

def get_average_instability(probs):
    """
    Instability is the extend to which the bootstrapped models
    give a different prediction from the model under test. The 
    average instability is an average of the SMAPE between
    the prediction of the model-under-test and the predictions of
    each of the other bootstrap models (i.e. pairing the model-under-test)
    with a single bootstrapped model gives one SMAPE value, and 
    these are averaged over all the bootstrap models).
    
    SMAPE is preferable to mean relative error, because the latter
    diverges when the prediction from the model-under-test is very small.
    It may however be better still to use the log of the accuracy ratio;
    see https://en.wikipedia.org/wiki/Symmetric_mean_absolute_percentage_error,
    since the probabilities are all positive (or maybe there is a better 
    thing for comparing probabilities specifically)
    
    Testing: not yet tested
    """
    num_rows = probs.shape[0]
    num_cols = probs.shape[1]
    
    smape_over_bootstraps = []
    
    # Loop over each boostrap model
    for j in range(1, num_cols):
        
        # Calculate SMAPE between bootstrap model j and
        # the model-under-test
        smape_over_bootstraps.append(smape(probs[:,0], probs[:,j]))

    return np.mean(smape_over_bootstraps)

def plot_instability(ax, probs, y_test, title="Probability stability"):
    """
    This function plots a scatter graph of one point
    per value in the test set (row of probs), where the
    x-axis is the value of the model under test (the
    first column of probs), and the y-axis is every other
    probability predicted from the bootstrapped models Mn
    (the other columns of probs). The predictions from
    the model-under-test corresponds to the straight line
    at 45 degrees through the origin

    For a stable model M0, the scattered points should be
    close to the M0 line, indicating that the bootstrapped
    models Mn broadly agree with the predictions made by M0.

    Testing: not yet tested
    """

    num_rows = probs.shape[0]
    num_cols = probs.shape[1]
    x = []
    y = []
    c = []
    for i in range(num_rows):
        for j in range(1, num_cols):
            x.append(probs[i, 0])  # Model-under-test
            y.append(probs[i, j])  # Other bootstrapped models
            c.append(y_test[i]),  # What was the actual outcome

    colour_map = {0: "g", 1: "r"}

    for outcome_to_plot, colour in colour_map.items():
       x_to_plot = [x for x, outcome in zip(x, c) if outcome == outcome_to_plot]
       y_to_plot = [y for y, outcome in zip(y, c) if outcome == outcome_to_plot]
       ax.scatter(x_to_plot, y_to_plot, c=colour, s=1, marker=".")

    ax.axline([0, 0], [1, 1])

    # You can restrict the axes here if you want
    #ax.set_xlim(0, 0.1)
    #ax.set_ylim(0,0.1)

    ax.legend(
        [   
            "Did not occur (background)",
            "Event occurred (foreground)",
        ],
        markerscale=15
    )
    ax.set_title(title)
    ax.set_xlabel("Prediction from model-under-test")
    ax.set_ylabel("Predictions from bootstrapped models")


def fit_model(Model, object_column_indices, X0_train, y0_train, M):
    """
    Fit the model given in the first argument to the training data
    (X0_train, y0_train) to produce M0. Then resample the training data M times
    (with replacement) to obtain M new training sets (Xm_train, ym_train), and
    fit M other models Mn. return the pair (M0, Mm) (the second element is a list
    of length M).
    """
    # Develop a single model from the training set (X0_train, y0_train),
    # using any method (e.g. including cross validation and hyperparameter
    # tuning) using training set data. This is referred to as D in
    # stability.py.
    print("Fitting model-under-test")
    M0 = Model(X0_train, y0_train, object_column_indices)

    # For the purpose of assessing model stability, obtain bootstrap
    # resamples (Xm_train, ym_train) from the training set (X0, y0).
    print("Creating bootstrap resamples of X0 for stability checking")
    Xm_train, ym_train = make_bootstrapped_resamples(X0_train, y0_train, M)

    # Develop all the bootstrap models to compare with the model-under-test M0
    print("Fitting bootstrapped models")
    Mm = [Model(X, y, object_column_indices) for (X, y) in zip(Xm_train, ym_train)]

    return (M0, Mm)


import schemdraw
from schemdraw import flow
import schemdraw.elements as elm
import matplotlib.pyplot as plt

def draw_experiment_plan(num_rows, num_train, num_test, num_folds, num_bootstraps):
    pad = 0.5
    main_height = 3.5
    main_width = 3*main_height
    arrow_size = 0.7

    with schemdraw.Drawing() as d:
        d.config(fontsize=10, unit=0.75*main_width)
        d += (d1 := flow.Box(w=main_width, h=main_height, E='YES', S='NO').anchor("S").label(f"Initial dataset\nN = {num_rows}"))
        d += flow.Arrow(headwidth=arrow_size,headlength=arrow_size).down(d.unit/2)
        d += (d2 := flow.Box(w=main_width, h=main_height, E='YES', S='NO').label(f"Training set $P_0$\nN = {num_train}"))
        d += flow.Arrow(headwidth=arrow_size,headlength=arrow_size).length(d.unit/2)
        d += (d3 := flow.Box(w=main_width, h=main_height, E='YES', S='NO').label(f"Fit process $D$"))
        d += flow.Arrow(headwidth=arrow_size,headlength=arrow_size).at(d3.S).down(d.unit).label("Model $M_0$", ofst=(0,-1))

        # d += flow.Arrow(headwidth=arrow_size,headlength=arrow_size).length(d.unit/2)
        # d += (d7 := flow.Box(w=main_width, h=main_height, E='YES', S='NO').label(f"ROC Curves"))   
        
        d.here = (-2.2*d.unit, 0)
        d += (a1 := flow.Arrow(headwidth=arrow_size,headlength=arrow_size).length(d.unit/2))
        d += (d4 := flow.Box(w=1.5*main_width, h=1.5*main_height, E='YES', S='NO').label(f"Tune hyperparameters\n({num_folds}-fold cross-validation\noptimising ROC AUC)"))
        d += flow.Arrow(headwidth=arrow_size,headlength=arrow_size).length(d.unit/2)
        d += (d5 := flow.Box(w=1.5*main_width, h=main_height, E='YES', S='NO').label(f"Fit model with\nbest parameters"))
        d += (a2 := flow.Arrow(headwidth=arrow_size,headlength=arrow_size).length(d.unit/2))
        d += (parallel := elm.EncircleBox([a1, d4, d5, a2], padx=pad, pady=pad).linestyle('--').linewidth(1).color('red').label("Model fitting process $D$"))
        
        #d.here = d2.E
        d += (a1 := flow.Arrow(headwidth=arrow_size,headlength=arrow_size).at(d2.E).right(0.8*d.unit))
        d += (d9 := flow.Box(w=main_width, h=main_height, E='YES', S='NO').label(f"Resample with\nreplacement"))   
        d += flow.Arrow(headwidth=arrow_size,headlength=arrow_size).at(d9.S).down(d.unit/2)
        d += (d10 := flow.Box(w=main_width, h=main_height, E='YES', S='NO').label(f"Fit process $D$"))  
        d += (parallel := elm.EncircleBox([d9, d10], padx=pad, pady=pad).linestyle('--').linewidth(1).color('blue').label(f"Repeat\n{num_bootstraps} times", "E"))
        d += flow.Arrow(headwidth=arrow_size,headlength=arrow_size).length(1*d.unit).label("Models $M_n$", ofst=(0,-1))
        d += (d6 := flow.Box(w=4*main_width, h=2*main_height, E='YES', S='NO').label(f"ROC curves: $M_0$ bold, $M_n$ faint\nRisk stability: risk from $M_n$ vs. risk from $M_0$\nCalibration: $M_0$ bold, $M_n$ faint"))   
    
        d += flow.Arrow(headwidth=arrow_size,headlength=arrow_size).right(d.unit*3).at(d1.E)
        d += (d8 := flow.Box(w=main_width, h=main_height).anchor('W').label(f'Testing set $T$\nN = {num_test}'))
        d += flow.Arrow(headwidth=arrow_size,headlength=arrow_size).at(d8.S).down(2*d.unit + 2*main_height)
        
    plt.show()