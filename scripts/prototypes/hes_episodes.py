# HES episodes-only dataset
#
# This script contains functions which convert the
# raw data retrieved from a hospital episode statistics
# table to a feature and outcome matrix (X,Y) which
# contains acute coronary syndrome index events (one per
# row of X and Y), counts of which diagnosis code groups
# occur before the index event (columns of X), other
# information about the patient and index event (columns
# of X), and whether or not a bleeding event or adverse
# cardiovascular event occurred after the index (columns
# of Y).
#

import os

os.chdir("scripts/prototypes")

import importlib
import datetime as dt

from py_hic.clinical_codes import get_codes_in_group, ClinicalCodeParser
import code_group_counts as codes

import hes

importlib.reload(hes)
importlib.reload(codes)

import re
import numpy as np


# Define the start and end date for collection of raw
# episodes data from the database. Use these variables to
# reduce the total amount of data to something the script
# can handle
start_date = dt.date(2017, 1, 1)
end_date = dt.date(2023, 1, 1)

# Fetch the raw data. 6 years of data takes 283 s to fetch (from home),
# so estimating full datasets takes about 1132 s. Same query took 217 s
# in ICB.
raw_episodes_data = hes.get_hes_data(start_date, end_date, "episodes")
raw_episodes_data.replace("", np.nan, inplace=True)
raw_episodes_data["episode_id"] = raw_episodes_data.index

# Find the last date seen in the dataset to use as an approximation for
# the right-censor date for the purpose of survival analysis.
right_censor_date = raw_episodes_data["episode_start_date"].max()

# Also helpful to know the earliest date in the dataset. This is important
# for whether it is possible to know predictors a certain time in advance.
left_censor_date = raw_episodes_data["episode_start_date"].min()

# Mapping from episode_id to patient. Required later for joining
# episodes together from different tables by patient. The order
# matches the raw_episode_data order.
patients = raw_episodes_data[["patient_id"]]

# Get all the clinical codes in long format, with a column to indicate
# whether it is a diagnosis or a procedure code. Note that this is 
# currently returning slightly less rows than raw_episode_data, 
# maybe if some rows contain no codes at all? More likely a bug -- to check.
long_clinical_codes = hes.convert_codes_to_long(raw_episodes_data, "episode_id")


code_groups = codes.get_code_groups(
    "../codes_files/icd10.yaml", "../codes_files/opcs4.yaml"
)

# Count the total number of clinical code groups in each episode. This is
# achieved by joining the names of the code groups onto the long codes 
# where the type (diagnosis or procedure) matches and also the normalised
# code (e.g. i211) matches. The groups are pivoted to become columns,
# with values equal to the number of occurrences of each group in each
# episode. Due to the inner join of groups onto episodes, any episode with
# not group will be dropped. These must be added back on at the end as
# zero rows.
code_group_counts = long_clinical_codes.merge(
    code_groups,
    how="inner",
    left_on=["clinical_code_type", "clinical_code"],
    right_on=["type", "name"],
)[["episode_id", "group"]].pivot_table(
    index="episode_id", columns="group", aggfunc=len, fill_value=0
)

idx_episodes = code_group_counts.join(raw_episodes_data, how = "left", on = "episode_id")