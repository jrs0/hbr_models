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
# What is required is a function that wraps the entire model
# into one call, taking as input the bootstrapped resample Pn and
# providing as output the bootstrapped model Mn. This function can
# then be called N times to generate the bootstrapped models.
#
# An aggregating function will then take all the models Mn, the 
# model-under-test M0, and the test set T, and make predictions
# using all the models for each sample in the test set. It should
# return all these predictions (probabilities) in a 2D array, where
# each row corresponds to a test-set sample, column 0 is the probability
# from M0, and columns 1 through M are the probabilites from each Mn.
#
# This 2D array may be used as the basis of instability plots.




