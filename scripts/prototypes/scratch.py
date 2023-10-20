# This file is scratch/working area for trying things out.
# Feel free to delete it all

import os
os.chdir("scripts/prototypes")

import save_datasets as ds

import importlib
importlib.reload(ds)


dataset = ds.Dataset("manual_codes_swd", "config.yaml", False)

X = dataset.get_X()

# outcome = hussain_ami_stroke_outcome
y = dataset.get_y("bleeding_al_ani_outcome")


a = ds.load_dataset_interactive("manual_codes_swd")