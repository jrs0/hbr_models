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

import pandas as pd

from py_hic.clinical_codes import get_codes_in_group, ClinicalCodeParser

import hes
import mortality as mort
import save_datasets as ds

importlib.reload(hes)
importlib.reload(mort)
importlib.reload(codes)
importlib.reload(ds)

import numpy as np

# Define the start and end date for collection of raw
# episodes data from the database. Use these variables to
# reduce the total amount of data to something the script
# can handle
start_date = dt.date(2014, 1, 1)  # Before the start of the data
end_date = dt.date(2024, 1, 1)  # After the end of the data
from_file = True

# Dataset containing one row per episode, grouped into spells by
# spell_id, with some patient demographic information (age and gender)
# and (predominantly) diagnosis and procedure columns
raw_episodes_data = hes.get_raw_episodes_data(start_date, end_date, from_file)

# Get all the clinical codes in long format, with a column to indicate
# whether it is a diagnosis or a procedure code. Note that this is
# currently returning slightly less rows than raw_episode_data,
# maybe if some rows contain no codes at all? More likely a bug -- to check.
long_clinical_codes = hes.convert_codes_to_long(raw_episodes_data, "episode_id")

# Convert the diagnosis and procedure columns into
code_group_counts = hes.make_code_group_counts(long_clinical_codes, raw_episodes_data)

# Get the latest (right censor) and earliest (left censor) dates seen
# in the data set
right_censor_date, left_censor_date = hes.get_censor_dates(raw_episodes_data)

raw_mortality_data = mort.get_mortality_data(start_date, end_date)
raw_mortality_data.replace("", np.nan, inplace=True)
# Not sure why this is necessary, it doesn't seem necessary with the episodes
raw_mortality_data["patient_id"] = raw_mortality_data["patient_id"].astype(np.int64)

# To find out whether a patient has died in the follow-up period
mortality_dates = raw_mortality_data[["patient_id", "date_of_death"]]

# Convert the wide primary/secondary cause of death columns
# to a long format of normalised ICD-10 codes (with position
# column indicating primary/secondary position).
long_mortality = mort.convert_codes_to_long(raw_mortality_data)

# Drop duplicate ICD-10 cause of death values by retaining only
# the highest priority value (the one with the lowest position).
# This information is used to find the cause of death if necessary
long_mortality = long_mortality.loc[
    long_mortality.groupby(["patient_id", "cause_of_death"])["position"].idxmin()
].reset_index(drop=True)

# Find the index episodes, which are the ones that contain an ACS or PCI and
# are also the first episode of the spell.
idx_episodes = hes.get_index_episodes(code_group_counts, raw_episodes_data)

# Get a table of index events paired up with all the patient's
# other episodes.
time_to_episode = hes.calculate_time_to_episode(idx_episodes, raw_episodes_data)

# This table contains the total number of each diagnosis and procedure
# group in a period before the index event. This could be the previous
# 12 months, excluding the month before the index event (to account for
# lack of coding data in that period)
max_period_before = dt.timedelta(days=365)  # Limit count to previous 12 months
min_period_before = dt.timedelta(days=31)  # Exclude month before index (not coded yet)
episodes_before = hes.get_episodes_before_index(
    time_to_episode, min_period_before, max_period_before
)

# Get a table of how many of each code group occurred before each index event
feature_counts = hes.get_code_groups_before_index(
    episodes_before, code_group_counts, idx_episodes
)

# Instead, get a sparse representation of all the codes (dummy-encoded)
# before the index event. This has about 7000 columns, each one is 1 if
# the code is present before index, and zero otherwise.
feature_any_code = hes.get_all_codes_before_index(
    episodes_before, long_clinical_codes, idx_episodes
)

# Plot the distribution of codes over the index episodes. The envelope on the
# right follows from assigning column indices in order of code-first-seen, which
# naturally biases in favour of more common codes.
# import seaborn as sns
# import matplotlib.pyplot as plt

# s = sns.heatmap(any_code_before)
# s = s.set(
#     xlabel="Diagnosis/Procedure Codes",
#     ylabel="Index Episode ID",
#     title="Distribution of Diagnosis/Procedure Codes",
# )
# plt.show()

# This table contains the total number of each diagnosis and procedure
# group in a period after the index event. A fixed window immediately
# after the index event is excluded, to filter out peri-procedural
# outcomes or outcomes that occur in the index event itself. A follow-up
# date is defined that becomes the "outcome_occurred" column in the
# dataset, for classification models.
follow_up = dt.timedelta(days=365)  # Limit "occurred" column to 12 months
min_period_after = dt.timedelta(days=31)  # Exclude the subsequent 72 hours after index

# Outcome column all_cause_death_outcome
all_cause_death = mort.get_all_cause_death(idx_episodes, mortality_dates, follow_up)

episodes_after = hes.get_episodes_after_index(
    time_to_episode, min_period_after, follow_up
)

# Compute the outcome columns based on the following code groups
outcome_groups = [
    "bleeding_al_ani",
    "bleeding_cadth",
    "bleeding_adaptt",
    "acs_bezin",
    "hussain_ami_stroke",
]
outcome_counts = hes.make_outcomes(
    outcome_groups, idx_episodes, episodes_after, code_group_counts
)

# Make the dataset whose feature columns are code groups defined in the
# icd10.yaml and opcs4.yaml file, and whose outcome columns are defined
# in the list above, along with all-cause mortality.
hes_code_groups_dataset = hes.make_dataset_from_features(
    idx_episodes, feature_counts, outcome_counts, all_cause_death
)
ds.save_dataset(hes_code_groups_dataset, "hes_code_groups_dataset")

# Make the sparse all-code features dataset
hes_all_codes_dataset = hes.make_dataset_from_features(
    idx_episodes, feature_any_code, outcome_counts, all_cause_death
)
ds.save_dataset(hes_all_codes_dataset, "hes_all_codes_dataset")
