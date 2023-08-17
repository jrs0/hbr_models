import os
os.chdir("scripts/prototypes")

import hes
import importlib

importlib.reload(hes)

####### FETCH RAW SPELL DATA #######

# Polars is slightly slower than pandas here, but polars
# returns the nhs_number column as an int not a float (that
# bigint problem again), so preferring polars for now. Both
# queries are really slow compared to R -- not sure why yet.
pd_data = hes.get_spells_hes_pandas()
pl_data = hes.get_spells_hes_polars()


