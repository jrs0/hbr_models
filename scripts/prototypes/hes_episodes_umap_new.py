# Extraction of common features among HES spells using UMAP
# (uniform manifold approximation and projection)
#
#

import os

os.chdir("scripts/prototypes")

import hes
import sparse_encode as spe

import importlib
import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import umap
import umap.plot
from sklearn.preprocessing import OneHotEncoder
import re

importlib.reload(hes)
importlib.reload(spe)

raw_data = hes.get_spells_hes_pandas()

cols_to_remove = ["nhs_number", "spell_start_date", "spell_end_date"]
df = raw_data.replace("", np.nan).drop(columns=cols_to_remove, axis=1)

age_and_gender = df[["spell_id", "age", "gender"]]

long_codes = hes.convert_codes_to_long(df)

#highest_priority_position = long_codes.groupby(["spell_id", "full_code"]).position.transform(min)
#long_codes_dedup = long_codes[long_codes.position == highest_priority_position]
long_codes_dedup = long_codes.groupby(["spell_id", "full_code"]).min().reset_index()

# Map the position onto the following linear scale: primary diagnosis
# is 24, through secondary_diagnosis_23 is 1 (same for procedure). The
# intention is to later create a linear scale where a higher number
# means a higher priority diagnosis or procedure, and the value 0 is
# reserved for diagnosis or procedure not present
linear_position = hes.make_linear_position_scale(long_codes_dedup, 23)

# It is too memory-intensive to just encode all the values
# in one go. Instead, filter the low-frequency codes first,
# then perform the encoding.
#
# Found I don't need this now that I've got sparse=True in
# the get_dummies call. There is also a mistake here -- you
# will drop spells that have no common codes, which might
# be a mistake.
counts = linear_position.full_code.value_counts() / len(linear_position)
most_frequent_codes = counts.head(1000).index.to_list()
reduced_codes = linear_position[linear_position.full_code.isin(most_frequent_codes)]

# Calculate a sparse encoded representation of the codes where
encoded, spell_ids = spe.encode_sparse(reduced_codes)

# Get the list of ages in the same order as the encoded data
ordered_spells = pd.DataFrame({"spell_id": spell_ids})
age = ordered_spells.merge(age_and_gender, on = "spell_id")

# Only keep the two 3 diagnosis and procedure codes, under the
# assumption that the others may contribute more noise than
# structure, or that the top codes may contain the most
# important information
top_three_codes = long_codes[long_codes.position < 3]

# There is an issue where the same code can show up in different
# positions. Pick the smallest position (higher priority).
# TODO figure out what is going on here
linear_position_dedup = linear_position.groupby(["spell_id", "full_code"]).min().reset_index()

# Create dummy variables for all the different codes
#
# This line takes quite a long time with relatively few codes, and
# should probably be optimised. The C++ approach of just passing
# through the vector once and building a numpy array row by row might 
# be fine. 
encoded = pd.get_dummies(reduced_codes, columns=["full_code"]).groupby("spell_id").max()

# Pivot to keep the diagnosis position as the value of the code,
# instead of just a TRUE/FALSE. The value after this pivot is the
# linear diagnosis/procedure scale from 1 (last secondary) to 24
# (primary), with NA when the code is not present in the spell.
encoded = linear_position.pivot(index = "spell_id", columns = "full_code", values = "position")
# Replace NA with 0 to indicate no code
#encoded = encoded.fillna(0)

# Now join this reduced encoded version back onto all the
# spells to get NaNs, which can be replaced with zero (indicating
# no code in that spell). Replace 0 with False when using dummy
# encoding
full_encoded = age_and_gender.join(encoded).fillna(False)

# No need to normalise, all the columns are on the same
# scale (binary, with hamming distance between rows).


# UMAP has the following parameters:
#
# - n_neighbors: this is the number of nearest neighbors to
#   use in the approximation of a uniform distance around 
#   each data point in the original manifold. Choosing a
#   a large number will course-grain the manifold, so that
#   the uniform distances are approximated over larger groups
#   of spells. 
# - min_dist: in the dimension-reduced manifold (after projection
#   from the original manifold), the local-connectedness condition
#   which translated to assuming that each data point is 0 distance
#   away from its nearest neighbour, must translate to an arbitrary
#   choice for what this minimum distance is in the Euclidean plane.
#   Making it small will cause more clustering, whereas making it 
#   large will push points away from each other, which may focus
#   more on the overall topological structure.
# - n_components: the n here is the dimension of the reduced space,
#   which is the manifold R^n with the standard topology arising
#   from Eucliean distances
# - metric: which metric is used to measure distance between the
#   different points of the dataset in the original (ambient)
#   space R^m (m is the number of columns in the original dataset).
#   Here, there is one binary column per clinical code, and two rows
#   (spells) are considered different according to how many of their
#   clinical codes differ -- this is the Hamming distance.

mapper = umap.UMAP(metric='euclidean', random_state=1, verbose = True)
res = mapper.fit(encoded)

umap.plot.points(res, values=age.age, theme='viridis')
plt.show()


embedding = mapper.fit_transform(encoded)
plt.scatter(
    embedding[:, 0],
    embedding[:, 1])
plt.gca().set_aspect('equal', 'datalim')
plt.title('UMAP projection of HES spell codes', fontsize=24)
plt.show()

# 2D embedding
fit = umap.UMAP(
    n_neighbors = 50,
    min_dist = 0.1,
    n_components = 2,
    #metric = "euclidean"
)
data_to_reduce = full_encoded.filter(regex="(icd10|opcs4)") # Use "full_code" for dummy encoding
embedding2d = fit.fit_transform(data_to_reduce)
embedding2d.shape
plt.scatter(
    embedding2d[:, 0],
    embedding2d[:, 1],
    c=full_encoded["age"])
plt.gca().set_aspect('equal', 'datalim')
plt.title('UMAP projection of HES spell codes', fontsize=24)
plt.show()

embedding_old = embedding2d

# Apply UMAP to reduce to 3 dimensions
fit = umap.UMAP(
    n_neighbors = 15,
    min_dist = 0.1,
    n_components = 3,
    metric = "hamming"
)
embedding3d = fit.fit_transform(full_encoded)
embedding3d.shape

# 3D embedding
fig = plt.figure()
ax = fig.add_subplot(projection = '3d')
ax.scatter(
    embedding3d[:, 0],
    embedding3d[:, 1],
    embedding3d[:, 2])
plt.gca().set_aspect('equal', 'datalim')
plt.title('UMAP projection of HES spell codes', fontsize=24)
plt.show()
