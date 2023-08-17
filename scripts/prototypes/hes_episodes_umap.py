import os

os.chdir("scripts/prototypes")

import hes
import importlib
import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
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
# columns (currently conflates diagnoses with procedures -
# to fix).
long_codes = pd.melt(df, id_vars=index_cols, value_vars=code_cols).dropna().drop(columns="variable")
long_codes.value = long_codes.value.apply(normalise_code)

# It is too memory-intensive to just encode all the values
# in one go. Instead, filter the low-frequency codes first,
# then perform the encoding.
#
# Found I don't need this now that I've got sparse=True in
# the get_dummies call. There is also a mistake here -- you
# will drop spells that have no common codes, which might
# be a mistake.
counts = long_codes.value.value_counts() / len(long_codes)
most_frequent_codes = counts.head(1000).index.to_list()
reduced_codes = long_codes[long_codes.value.isin(most_frequent_codes)]
    
encoded = reduced_codes[['spell_id']].join(pd.get_dummies(reduced_codes['value'], sparse = True)).groupby('spell_id').max()

encoded = pd.get_dummies(long_codes, columns=["value"], sparse = True)

reducer = umap.UMAP()
