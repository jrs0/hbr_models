# This file is scratch/working area for trying things out.
# Feel free to delete it all

import os
os.chdir("scripts/prototypes")

import save_datasets as ds
import numpy as np
from sklearn.model_selection import train_test_split
from stability import fit_model, predict_bootstrapped_proba
import models

import stability

import importlib
importlib.reload(ds)
importlib.reload(stability)
importlib.reload(models)

ds.get_file_list("manual_codes_swd")

dataset = ds.Dataset("manual_codes_swd", "config.yaml", False)

# Store the indices of columns which need to be dummy encoded.
# This is passed to the models, which do the encoding as a 
# preprocessing step.
object_column_indices = dataset.object_column_indices

# Get the feature matrix X and outcome vector y
X = dataset.get_X()

# outcome = hussain_ami_stroke_outcome
y = dataset.get_y("bleeding_al_ani_outcome")

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

#Model = models.SimpleLogisticRegression
Model = models.TruncSvdLogisticRegression

# Fit the model-under-test M0 to the training set (X0_train, y0_train), and
# fit M other models to M other bootstrap resamples of (X0_train, y0_train).
M0, Mm = stability.fit_model(Model, object_column_indices, X0_train, y0_train, M=10)

print(M0.get_model_parameters())