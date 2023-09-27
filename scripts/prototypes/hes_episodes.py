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
# Now I've found that there doesn't appear to be any issue --
# at least in this commit (93002f42), rerunning this script and
# generating new saved data (in datasets/) produces models that
# are back to normal (ROC 0.64). However, I changed nothing in
# this commit, so I went back and regenerated data in older
# commits. I found by checking commits 04feda130ed17 and
# 53e3810b381bc and regenerating the data in those commits that
# the bug was never present. That means that the bug was in an
# earlier version of the dataset saved in datasets/, but they
# are tagged by timestamp and commit, so I am going to find
# which one caused the problem. Hopefully this will point to
# a commit with the error, which I can diff with this one.
# Identified that the erroneous file came from commit 213adc33035;
# however, looking at the diff doesn't show anything obvious that is
# wrong. Going to checkout to that commit and rerun the dataset to
# see if it does contain a problem. Unfortunately, that commit appears
# to generate data correctly, which means the issue was probably
# some spurious way the script was run interactively at the time.
# Going to stop investigating.

import os

os.chdir("scripts/prototypes")

import importlib
import datetime as dt

import pandas as pd

from py_hic.clinical_codes import get_codes_in_group, ClinicalCodeParser
import code_group_counts as codes

import hes
import mortality
import save_datasets as ds

importlib.reload(hes)
importlib.reload(mortality)
importlib.reload(codes)
importlib.reload(ds)

import numpy as np

# Define the start and end date for collection of raw
# episodes data from the database. Use these variables to
# reduce the total amount of data to something the script
# can handle
start_date = dt.date(2014, 1, 1)  # Before the start of the data
end_date = dt.date(2024, 1, 1)  # After the end of the data

# Fetch the raw data. 6 years of data takes 283 s to fetch (from home),
# so estimating full datasets takes about 1132 s. Same query took 217 s
# in ICB. Fetching the full dataset takes 1185 s (measured at home),
# and returns about 10.8m rows. However, excluding rows according to
# documented exclusions results in about 6.7m rows, and takes about
# 434 s to fetch (from home)
raw_episodes_data = hes.get_hes_data(start_date, end_date, "episodes")
raw_episodes_data.to_pickle("datasets/raw_episodes_dataset_small.pkl")

# Optional, read from pickle instead of sql fetch
raw_episodes_data = pd.read_pickle("datasets/raw_episodes_dataset_small.pkl")

# TODO remove NaNs in the spell_id column. There aren't that many,
# but it could mess up the logic later on.

raw_episodes_data.replace("", np.nan, inplace=True)
raw_episodes_data["episode_id"] = raw_episodes_data.index

code_groups = codes.get_code_groups(
    "../codes_files/icd10.yaml", "../codes_files/opcs4.yaml"
)

# Get all the clinical codes in long format, with a column to indicate
# whether it is a diagnosis or a procedure code. Note that this is
# currently returning slightly less rows than raw_episode_data,
# maybe if some rows contain no codes at all? More likely a bug -- to check.
long_clinical_codes = hes.convert_codes_to_long(raw_episodes_data, "episode_id")

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

del long_clinical_codes

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

age_and_gender = raw_episodes_data[["episode_id", "age", "gender"]]

raw_mortality_data = mortality.get_mortality_data(start_date, end_date)
raw_mortality_data.replace("", np.nan, inplace=True)
# Not sure why this is necessary, it doesn't seem necessary with the episodes
raw_mortality_data["patient_id"] = raw_mortality_data["patient_id"].astype(np.int64)

# To find out whether a patient has died in the follow-up period
mortality_dates = raw_mortality_data[["patient_id", "date_of_death"]]

# Convert the wide primary/secondary cause of death columns
# to a long format of normalised ICD-10 codes (with position
# column indicating primary/secondary position).
long_mortality = mortality.convert_codes_to_long(raw_mortality_data)

# Drop duplicate ICD-10 cause of death values by retaining only
# the highest priority value (the one with the lowest position).
# This information is used to find the cause of death if necessary
long_mortality = long_mortality.loc[
    long_mortality.groupby(["patient_id", "cause_of_death"])["position"].idxmin()
].reset_index(drop=True)

# Find the index episodes, which are the ones that contain an ACS or PCI and
# are also the first episode of the spell.
# NOTE: there appear to be duplicate spell IDs; i.e., episodes separated
# by like 5 years, with the same spell ID, but no other intervening episodes.
# Doesn't sound likely that someone is in hospital for 5 years with only two
# consultant episodes.
df = (
    code_group_counts.merge(
        raw_episodes_data[["episode_id", "spell_id", "episode_start_date"]],
        how="left",
        on="episode_id",
    )
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
idx_episodes["idx_pci_performed"] = df["pci"] > 0
idx_episodes["idx_stemi"] = df["mi_stemi_schnier"] > 0
idx_episodes["idx_nstemi"] = df["mi_nstemi_schnier"] > 0
idx_episodes["idx_acs"] = df["acs_bezin"] > 0
idx_episodes = (
    idx_episodes.merge(
        episode_start_dates, how="left", left_on="idx_episode_id", right_on="episode_id"
    )
    .merge(age_and_gender, how="left", left_on="idx_episode_id", right_on="episode_id")
    .rename(
        columns={
            "episode_start_date": "idx_date",
            "age": "dem_age",
            "gender": "dem_gender",
        }
    )
    .filter(regex="(idx_|dem_|patient_id)")
)

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

# Find which index episodes were followed by all-cause death within
# the follow-up period
df = idx_episodes.merge(mortality_dates, how="left", on="patient_id")
df["all_cause_death_outcome"] = ~df["date_of_death"].isna() & (
    pd.to_datetime(df["date_of_death"]) - df["idx_date"] < follow_up
)
all_cause_death = df[["idx_episode_id", "all_cause_death_outcome"]]

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
outcome_groups = [
    "bleeding_al_ani",
    "bleeding_cadth",
    "bleeding_adaptt",
    "acs_bezin",
    "hussain_ami_stroke",
]
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
code_counts_after["bleeding_cadth_outcome"] = code_counts_after[
    "bleeding_cadth_outcome"
].astype(bool)
code_counts_after["bleeding_adaptt_outcome"] = code_counts_after[
    "bleeding_adaptt_outcome"
].astype(bool)
code_counts_after["acs_bezin_outcome"] = code_counts_after["acs_bezin_outcome"].astype(
    bool
)
code_counts_after["hussain_ami_stroke_outcome"] = code_counts_after[
    "hussain_ami_stroke_outcome"
].astype(bool)

# Now combine the information into a final dataset containing both X and y
dataset = (
    idx_episodes.merge(code_counts_before, how="left", on="idx_episode_id")
    .merge(code_counts_after, how="left", on="idx_episode_id")
    .merge(all_cause_death)
    .drop(columns=["idx_episode_id", "idx_spell_id", "patient_id", "idx_date"])
)

# Save the resulting dataset
ds.save_dataset(dataset, "hes_episodes_dataset_small")
