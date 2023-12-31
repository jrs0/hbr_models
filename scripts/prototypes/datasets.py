# ACS Dataset 
#
# This script creates a set of datasets for ACS index events,
# bleeding and ischaemia outcomes, and features, from hospital
# episode statistics (HES) and the BNSSGG primary care attributes
# table, derived from OneCare (GP) data. After running this script,
# the datasets are saved in the scripts/prototypes/datasets/, and
# are named as follows:
#
# 1. manual_codes.pkl:
#   index definition: ACS and PCI code groups from HES 
#   outcomes: 2-point MACE (AMI and stroke) code groups from HES
#   features: manually chosen code groups from HES
#             age and gender from HES
#
# 2. all_codes.pkl:
#   index definition: ACS and PCI code groups from HES 
#   outcomes: 2-point MACE (AMI and stroke) code groups from HES
#   features: all HES diagnosis and procedure codes as separate columns
#             age and gender from HES
# 
# 3. manual_codes_swd.pkl:
#   index definition: ACS and PCI code groups from HES 
#   outcomes: 2-point MACE (AMI and stroke) code groups from HES
#   features: manually chosen code groups from HES
#             age and gender from HES
#             patient attributes from GP data, just prior to index
#
# Datasets 1. and 2. have the same number of rows, and differ only in
# the processing of the feature columns (manual code groups vs. one
# column per clinical code). Dataset 3. has less rows due to the reduced
# date range of the primary care attributes table. All tables have the
# same index events (apart from the date restriction), and the same outcomes
# for each index event.
#

import os

os.chdir("scripts/prototypes")

import importlib
import datetime as dt

import pandas as pd

from py_hbr.clinical_codes import get_codes_in_group, ClinicalCodeParser

import hes
import swd
import mortality as mort
import save_datasets as ds

importlib.reload(swd)
importlib.reload(hes)
importlib.reload(mort)
# importlib.reload(codes)
importlib.reload(ds)

import numpy as np

# Define the start and end date for collection of raw
# episodes data from the database. Use these variables to
# reduce the total amount of data to something the script
# can handle
start_date = dt.date(1995, 1, 1)  # Before the start of the data
end_date = dt.date(2025, 1, 1)  # After the end of the data
from_file = True

# These four time periods define what events are considered index events,
# what events are considered to follow or precede index events, what
# exclusion is used directly before the index event to account for coding
# time, and any exclusion directly after the index for periprocedural
# events.
#
# Index events are only considered if they include a full max_period_before
# before the index date and follow_up period after the index date. These are
# calculated with respect to the left_censor_date and right_censor_date, which
# are the first and last dates seen in the dataset, and are taken to mean the
# start and end of the full dataset period. Note that this makes the assumption
# that the first and last dates are usable as indicators for the period of
# time when a patient might have had data recorded about them. In practice, it
# may be more valid on the right_censor side (recent data) than the left censor
# side (which might have spurious data back to the 1990s).
#
max_period_before = dt.timedelta(days=365)  # Limit count to previous 12 months
min_period_before = dt.timedelta(days=31)  # Exclude month before index (not coded yet)
follow_up = dt.timedelta(days=365)  # Limit "occurred" column to 12 months
min_period_after = dt.timedelta(hours=72)  # Exclude the subsequent 72 hours after index

# Define a window before the index event where SWD attributes will be considered valid.
# 41 days is used to ensure that a full month is definitely captured. Consider
# using 31*n + 10 to allow attributes up to n months before the index event to be used
# (the most recent attributes will still be preferred).
attribute_valid_window = dt.timedelta(days=41)

# Fetching all the attributes data
# raw_attributes_data = swd.get_attributes_data(start_date, end_date)
# raw_attributes_data.to_pickle("datasets/raw_attributes_data.pkl")

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
# From the guidance document: "a small number of duplicates are present in the dataset - "
# "this is the case for around 55 entries. The cause for these is unknown and is under "
# "investigation".
raw_mortality_data = raw_mortality_data.groupby("patient_id").filter(
    lambda x: len(x) == 1
)

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

# Exclude those index events which do not have a full follow_up period after
# the index event, and do not have a full max_period_before before the index
# event
idx_episodes = idx_episodes[
    ((right_censor_date - idx_episodes.idx_date) > follow_up)
    & ((idx_episodes.idx_date - left_censor_date) > max_period_before)
]

# Get a table of index events paired up with all the patient's
# other episodes.
time_to_episode = hes.calculate_time_to_episode(idx_episodes, raw_episodes_data)

# This table contains the total number of each diagnosis and procedure
# group in a period before the index event. This could be the previous
# 12 months, excluding the month before the index event (to account for
# lack of coding data in that period)
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
manual_codes = hes.make_dataset_from_features(
    idx_episodes, feature_counts, outcome_counts, all_cause_death
)
ds.save_dataset(manual_codes, "manual_codes")

# Make the sparse all-code features dataset
all_codes = hes.make_dataset_from_features(
    idx_episodes, feature_any_code, outcome_counts, all_cause_death
)
ds.save_dataset(all_codes, "all_codes")

# Now link the system-wide dataset attributes. An index event is included
# if it has a row of attributes in the SWD up to a month before the heart
# attack occurred.

# Load raw attributes data
patient_ids = idx_episodes["patient_id"].unique()
raw_attributes = swd.get_raw_attributes_data(
    start_date, end_date, patient_ids, from_file
)

# Remove index events where the patient is not in the attributes
swd_idx_episodes = idx_episodes[
    idx_episodes["patient_id"].isin(raw_attributes["patient_id"])
]

# Join the attributes onto the index episodes by patient, and then
# only keep attributes that are before the index event, but with
# the attribute_valid_window
#
# The attribute_period column of an attributes row indicates that
# the attribute was valid at the end of the interval
# (attribute_period, attribute_period + 1month). It is important
# that no attribute is used in modelling that could have occurred
# after the index event, meaning that attribute_period + 1 < idx_date
# must hold for any attribute used as a predictor. On the other hand,
# data substantially before the index event should not be used. The
# valid window is controlled by imposing
#
# (idx_date - attribute_period) < attribute_valid_window
#
# Ensure that attribute_valid_window is slightly larger than a multiple
# of months to ensure that a full month is captured.
#
df = (
    swd_idx_episodes.merge(
        raw_attributes[["patient_id", "attribute_period", "attribute_id"]],
        how="left",
        on="patient_id",
    )
    .groupby("idx_episode_id")
    .apply(
        lambda g: g[
            ((g["attribute_period"] + dt.timedelta(days=31)) < g["idx_date"])
            & ((g["idx_date"] - g["attribute_period"]) < attribute_valid_window)
        ]
    )
    .reset_index(drop=True)
    .drop(columns=["attribute_period"])
)

# Prepare the other attributes for joining as features
feature_attributes = raw_attributes.drop(columns=["patient_id", "attribute_period"])

# Now join on all the attributes by attribute_id, and the standard HES feature code
# groups and outcome columns
manual_codes_swd = (
    df.merge(feature_attributes, how="left", on="attribute_id")
    .merge(feature_counts, how="left", on="idx_episode_id")
    .merge(outcome_counts, how="left", on="idx_episode_id")
    .merge(all_cause_death, how="left", on="idx_episode_id")
    .set_index("idx_episode_id")
    .drop(columns=["idx_spell_id", "patient_id", "attribute_id"])
)

# Check that the primary care attributes age agrees with the HES age
# thoughout the dataset, then remove the SWD age columns. Allow a discrepancy
# of up to 1 year due to rounding. There are places where the age is out by
# one year, but in this version of the script this discrepancy is ignored.
age_not_equal = abs(manual_codes_swd["dem_age"] - manual_codes_swd["swd_age"] > 1)
num_age_not_equal = age_not_equal.sum()
print(f"Removing {num_age_not_equal} rows where HES age and primary care attributes disagree by more than 1 year")
manual_codes_swd = manual_codes_swd[~age_not_equal]
manual_codes_swd.drop(columns=["swd_age"], inplace=True)

# Also drop the gender/sex duplicate column -- might help models

ds.save_dataset(manual_codes_swd, "manual_codes_swd")