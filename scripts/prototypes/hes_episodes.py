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
#
# NOTE: this script is not working yet. Two things are odd:
# firstly, there seem way too many index events, which might
# be an error with the code groups/pivoting the code columns
# to long format. Secondly, the models for bleeding are way
# too good (AUC 90), so there is an issue with the predictors.

import os

os.chdir("scripts/prototypes")

import importlib
import datetime as dt

import pandas as pd

from py_hic.clinical_codes import get_codes_in_group, ClinicalCodeParser
import code_group_counts as codes

import hes
import save_datasets as ds

importlib.reload(hes)
importlib.reload(codes)
importlib.reload(ds)

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
raw_episodes_data.to_pickle("datasets/raw_episodes_dataset.pkl")

# Optional, read from pickle instead of sql fetch
raw_episodes_data = pd.read_pickle("datasets/raw_episodes_dataset.pkl")

# TODO remove NaNs in the spell_id column. There aren't that many,
# but it could mess up the logic later on.

raw_episodes_data.replace("", np.nan, inplace=True)
raw_episodes_data["episode_id"] = raw_episodes_data.index

# Find the last date seen in the dataset to use as an approximation for
# the right-censor date for the purpose of survival analysis.
right_censor_date = raw_episodes_data["episode_start_date"].max()

# Also helpful to know the earliest date in the dataset. This is important
# for whether it is possible to know predictors a certain time in advance.
left_censor_date = raw_episodes_data["episode_start_date"].min()

# Also need to know the episode start times for comparison of different
# episodes
episode_start_dates = raw_episodes_data[
    ["episode_id", "episode_start_date", "patient_id"]
]

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
# no codes in a group will be dropped. These must be added back on at
# the end as zero rows.
code_group_counts = (
    long_clinical_codes.merge(
        code_groups,
        how="inner",
        left_on=["clinical_code_type", "clinical_code"],
        right_on=["type", "name"],
    )[["episode_id", "group"]]
    .pivot_table(index="episode_id", columns="group", aggfunc=len, fill_value=0)
    .merge(raw_episodes_data["episode_id"], how="right", on="episode_id")
    .fillna(0)
)

### Visually checked the datasets up to here ###

# Find the index episodes, which are the ones that contain an ACS or PCI and
# are also the first episode of the spell.
df = (
    code_group_counts.merge(
        raw_episodes_data[["episode_id", "spell_id", "episode_start_date"]],
        how="left",
        on="episode_id",
    )
    # Is this an issue?
    .sort_values("episode_start_date")
    .groupby("spell_id")
    .first()
)
assert (
    df.shape[0] == raw_episodes_data.spell_id.nunique()
), "Expecting df to have one row per spell in the original dataset"
idx_episodes = (
    df[(df["acs_bezin"] > 0) | (df["pci"] > 0)]
    .reset_index()[["episode_id", "spell_id"]]
    .rename(columns={"episode_id": "idx_episode_id", "spell_id": "idx_spell_id"})
)

# Calculate information about the index event
df = idx_episodes.merge(
    code_group_counts, how="left", left_on="idx_episode_id", right_on="episode_id"
)
idx_episodes["pci_performed"] = df["pci"] > 0
idx_episodes["stemi"] = df["mi_stemi_schnier"] > 0
idx_episodes["nstemi"] = df["mi_nstemi_schnier"] > 0
idx_episodes["acs"] = df["acs_bezin"] > 0
idx_episodes = idx_episodes.merge(
    episode_start_dates, how="left", left_on="idx_episode_id", right_on="episode_id"
).rename(columns={"episode_start_date": "idx_date"})[
    [
        "idx_episode_id",
        "patient_id",
        "idx_date",
        "pci_performed",
        "stemi",
        "nstemi",
        "acs",
    ]
]

# Join all episode start dates by patient to get a table of index events paired
# up with all the patient's other episodes. This can be used to find which other
# episodes are inside an appropriate window before and after the index event
df = idx_episodes.merge(episode_start_dates, how="left", on="patient_id")
df["index_to_episode_time"] = df["episode_start_date"] - df["idx_date"]
time_to_episode = df[["idx_episode_id", "episode_id", "index_to_episode_time"]]

# This table contains the total number of each diagnosis and procedure
# group in a period before the index event. This could be the previous
# 12 months, excluding the month before the index event (to account for
# lack of coding data in that period)
max_period_before = dt.timedelta(days=365)  # Limit count to previous 12 months
min_period_before = dt.timedelta(days=31)  # Exclude month before index (not coded yet)

# These are the episodes whose clinical code counts should contribute
# to predictors.
df = time_to_episode[
    (time_to_episode["index_to_episode_time"] < -min_period_before)
    & (-max_period_before < time_to_episode["index_to_episode_time"])
]
episodes_before = df[["idx_episode_id", "episode_id"]]

# Compute the total count for each index event that has an episode
# in the valid window before the index. Note that this excludes
# index events with zero episodes before the index.
code_counts_before = (
    episodes_before.merge(code_group_counts, how="left", on="episode_id")
    .drop(columns="episode_id")
    .groupby("idx_episode_id")
    .sum()
    .add_suffix("_before")
    .merge(idx_episodes["idx_episode_id"], how="right", on="idx_episode_id")
    .fillna(0)
)

# This table contains the total number of each diagnosis and procedure
# group in a period after the index event. A fixed window immediately
# after the index event is excluded, to filter out peri-procedural
# outcomes or outcomes that occur in the index event itself. A follow-up
# date is defined that becomes the "outcome_occurred" column in the
# dataset, for classification models.
follow_up = dt.timedelta(days=365)  # Limit "occurred" column to 12 months
min_period_after = dt.timedelta(days=31)  # Exclude the subsequent 72 hours after index

# These are the subsequent episodes after the index, with
# the index row also retained. They are not limited to the follow-up
# period yet, because survival analysis can make use of times that are
# longer than the fixed follow-up. The follow_up is used later to create
# a classification outcome column
episodes_after = time_to_episode[
    # Exclude a short window after the index
    (time_to_episode["index_to_episode_time"] > min_period_after)
    # Drop events after the follow up period
    & (follow_up > time_to_episode["index_to_episode_time"])
][["idx_episode_id", "episode_id"]]

# Compute the outcome columns -- just classification for now
outcome_groups = ["bleeding_al_ani", "acs_bezin"]
code_counts_after = (
    episodes_after.merge(code_group_counts, how="left", on="episode_id")
    .drop(columns="episode_id")
    .groupby("idx_episode_id")
    .sum()
    .filter(outcome_groups)
    .add_suffix("_outcome")
    .merge(idx_episodes["idx_episode_id"], how="right", on="idx_episode_id")
    .fillna(0)
)

# Reduce the outcome to a True if > 0 or False if == 0
code_counts_after["bleeding_al_ani_outcome"] = code_counts_after[
    "bleeding_al_ani_outcome"
].astype(bool)
code_counts_after["acs_bezin_outcome"] = code_counts_after["acs_bezin_outcome"].astype(
    bool
)

# Now combine the information into a final dataset containing both X and y
dataset = (
    idx_episodes.merge(code_counts_before, how="left", on="idx_episode_id")
    .merge(code_counts_after, how="left", on="idx_episode_id")
    .drop(columns=["idx_episode_id", "patient_id", "idx_date"])
)

# Save the resulting dataset
ds.save_dataset(dataset, "hes_episodes_dataset")

d1 = ds.load_dataset("hes_episodes_dataset")
