# This file is scratch/working area for trying things out.
# Feel free to delete it all

import os
os.chdir("scripts/prototypes")

import summarise_model as s
import save_datasets as ds
import calibration as cal
import stability as stab

import importlib
importlib.reload(s)
importlib.reload(cal)
importlib.reload(stab)
importlib.reload(ds)

d = ds.load_dataset("all_codes", True)

d = ds.Dataset("all_codes", "config.yaml",True)

s.get_model_summary("manual_codes", "simple_logistic_regression", "bleeding_al_ani_outcome")
d = ds.load_fit_info("manual_codes_swd_simple_logistic_regression_bleeding_al_ani_outcome")

cal.get_average_calibration_error(d["probs"], d["y_test"], n_bins=10)

stab.get_average_instability(d["probs"])