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


# Define the start and end date for collection of raw
# episodes data from the database. Use these variables to
# reduce the total amount of data to something the script
# can handle
start_date = dt.date(2017,1,1)
end_date = dt.date(2023,1,1)

# Fetch the raw data. 6 years of data takes 283 s to fetch (from home),
# so estimating full datasets takes about 1132 s.
raw_episodes_data = hes.get_hes_data(start_date, end_date, "episodes")

# Find the last date seen in the dataset to use as an approximation for
# the right-censor date for the purpose of survival analysis.
right_censor_date = raw_episodes_data["episode_start_date"].max()

# Also helpful to know the earliest date in the dataset. This is important
# for whether it is possible to know predictors a certain time in advance.
left_censor_date = raw_episodes_data["episode_start_date"].min()
