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

sns.set(style='white', context='notebook', rc={'figure.figsize':(14,10)})

importlib.reload(hes)

####### FETCH RAW SPELL DATA #######

# Polars is slightly slower than pandas here, but polars
# returns the nhs_number column as an int not a float (that
# bigint problem again), so preferring polars for now. Both
# queries are really slow compared to R -- not sure why yet.
raw_data = hes.get_spells_hes_pandas()
#pl_data = hes.get_spells_hes_polars()
#raw_spells = pl_data.to_pandas()

####### CONVERT CODE COLUMNS TO DUMMIES #######

# Replace empty codes ("") with NaN, so that they are
# ignored in the conversion to dummies
df = raw_data.replace("", np.nan)

# First, replace all
df = pd.get_dummies(raw_data, columns = ["primary_diagnosis", "primary_procedure"], sparse = True)

categorical_cols = ['a', 'b', 'c', 'd'] 

reducer = umap.UMAP()