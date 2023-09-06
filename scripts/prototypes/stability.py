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
# Assuming a model development process that takes a training set 
# P0 that is used to develop a model M0 using a model development 
# process D (involving steps such cross-validation and 
# hyperparameter tuning in the training set, and validation of 
# accuracy of model prediction in the test set), the following steps
# are required to assess the stability of M0:
#
# 1. Bootstrap resample P0 with replacement M >= 200 times, creating 
#    M new datasets Pm that are all the same size as P0
# 2. Apply D to each Pm, to obtain M new models Mn which are all
#    comparable with M0.
# 3. Collect together the predictions from all Mn and compare them
#    to the predictions from M0 for each sample in the test set T.
# 4. From the data in 3, plot instability plots such as a scatter
#    plot of M0 predictions on the x-axis and all the Mn predictions
#    on the y-axis, for each sample of T.
#
#
