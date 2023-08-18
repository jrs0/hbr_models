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

sns.set(style="white", context="notebook", rc={"figure.figsize": (14, 10)})

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
cols_to_remove = ["nhs_number", "age", "gender", "spell_start_date", "spell_end_date"]
df = raw_data.replace("", np.nan).drop(columns=cols_to_remove, axis=1)

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
# columns
long_codes = pd.melt(df, id_vars=index_cols, value_vars=code_cols).dropna()
long_codes.value = long_codes.value.apply(normalise_code)
# Prepend icd10 or opc4 to the codes to indicate which are which
# (because some codes appear in both ICD-10 and OPCS-4)
pattern = re.compile("diagnosis")
long_codes['diagnosis_or_procedure'] = ["icd10_" if pattern.search(s) else "opcs4_" for s in long_codes.variable]
long_codes["full_code"] = long_codes.diagnosis_or_procedure + long_codes.value
long_codes = long_codes.drop(columns=["variable", "value", "diagnosis_or_procedure"])

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
    
encoded = reduced_codes[['spell_id']].join(pd.get_dummies(reduced_codes['full_code'], sparse=True)).groupby('spell_id').max()

encoded = pd.get_dummies(reduced_codes, columns=["full_code"]).groupby("spell_id").max()

# Now join this reduced encoded version back onto all the
# spells to get NaNs, which can be replaced with zero (indicating
# no code in that spell).
all_spells = df[["spell_id"]]
full_encoded = all_spells.join(encoded).fillna(False)


# No need to normalise, all the columns are on the same
# scale

# Get the age and gender by spell ID
age_and_gender = raw_data[["spell_id", "age", "gender"]]

# Join the age and gender to ensure that the rows are in the
# right order
dataset = age_and_gender.join(full_encoded)

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
#   clinical codes differe -- this is the Hamming distance.

# 2D embedding
fit = umap.UMAP(
    n_neighbors = 15,
    min_dist = 1,
    n_components = 2,
    metric = "hamming"
)
embedding2d = fit.fit_transform(full_encoded)
embedding2d.shape
plt.scatter(
    embedding2[:, 0],
    embedding2[:, 1],
    c=[sns.color_palette()[x] for x in full_encoded. map({"Adelie":0, "Chinstrap":1, "Gentoo":2})]))
plt.gca().set_aspect('equal', 'datalim')
plt.title('UMAP projection of HES spell codes', fontsize=24)
plt.show()

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
