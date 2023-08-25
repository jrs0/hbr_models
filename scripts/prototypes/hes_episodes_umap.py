# Extraction of common features among HES spells using UMAP
# (uniform manifold approximation and projection)
#
#

import os

os.chdir("scripts/prototypes")

import hes
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
from sklearn.preprocessing import OneHotEncoder
import re

importlib.reload(hes)

####### FETCH RAW SPELL DATA #######

# Polars is slightly slower than pandas here, but polars
# returns the nhs_number column as an int not a float (that
# bigint problem again), so preferring polars for now. Both
# queries are really slow compared to R -- not sure why yet.
raw_data = hes.get_spells_hes_pandas()
# pl_data = hes.get_spells_hes_polars()
# raw_spells = pl_data.to_pandas()

####### CONVERT CODE COLUMNS TO DUMMIES #######

# Replace empty codes ("") with NaN, so that they are
# ignored in the conversion to dummies
cols_to_remove = ["nhs_number", "spell_start_date", "spell_end_date"]
df = raw_data.replace("", np.nan).drop(columns=cols_to_remove, axis=1)

age_and_gender = df[["spell_id", "age", "gender"]]

pattern = re.compile("(diagnosis|procedure)")
code_cols = [s for s in df.columns if pattern.search(s)]
index_cols = ["spell_id"]

def normalise_code(code):
    '''
    Remove all whitespace and any dot character,
    and convert characters in the code to lower case.
    '''
    alpha_num = re.sub(r'\W+', '', code)
    return alpha_num.lower()

# Pivot all the diagnosis and procedure codes into one
# columns. Consider https://stackoverflow.com/questions/47684961/
# melt-uneven-data-in-columns-and-ignore-nans-using-pandas
# for speed.
long_codes = pd.melt(df, id_vars=index_cols, value_vars=code_cols).dropna()
long_codes.value = long_codes.value.apply(normalise_code)
# Prepend icd10 or opc4 to the codes to indicate which are which
# (because some codes appear in both ICD-10 and OPCS-4)
pattern = re.compile("diagnosis")
diagnosis_or_procedure = ["icd10_" if pattern.search(s) else "opcs4_" for s in long_codes.variable]
long_codes["full_code"] = diagnosis_or_procedure + long_codes.value
long_codes["position"] = long_codes["variable"].replace("(diagnosis|procedure)_", "", regex = True).astype(int)
long_codes = long_codes.drop(columns=["variable", "value"])

# Only keep the two 3 diagnosis and procedure codes, under the
# assumption that the others may contribute more noise than
# structure, or that the top codes may contain the most
# important information
long_codes = long_codes[long_codes.position < 3]

# Map the position onto the following linear scale: primary diagnosis
# is 24, through secondary_diagnosis_23 is 1 (same for procedure). The
# intention is to later create a linear scale where a higher number
# means a higher priority diagnosis or procedure, and the value 0 is
# reserved for diagnosis or procedure not present
#long_codes.position = 24 - long_codes.position

# It is too memory-intensive to just encode all the values
# in one go. Instead, filter the low-frequency codes first,
# then perform the encoding.
#
# Found I don't need this now that I've got sparse=True in
# the get_dummies call. There is also a mistake here -- you
# will drop spells that have no common codes, which might
# be a mistake.
counts = long_codes.full_code.value_counts() / len(long_codes)
most_frequent_codes = counts.head(1000).index.to_list()
reduced_codes = long_codes[long_codes.full_code.isin(most_frequent_codes)]

# Truncate instead of reducing
reduced_codes = long_codes.head(50000)

# There is an issue where the same code can show up in different
# positions. Pick the smallest position (higher priority).
# TODO figure out what is going on here
#reduced_codes = reduced_codes.groupby(["spell_id", "full_code"]).min().reset_index()

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
#encoded = reduced_codes.pivot(index = "spell_id", columns = "full_code", values = "position")
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

# 2D embedding
fit = umap.UMAP(
    n_neighbors = 15,
    min_dist = 0.1,
    n_components = 2,
    #metric = "euclidean"
    verbose = True
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
