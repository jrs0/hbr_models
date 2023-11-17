# Extraction of common features among HES spells using UMAP
# (uniform manifold approximation and projection)
#
#

import os

os.chdir("scripts/prototypes")

import importlib
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import umap
import umap.plot
import re
import scipy
import py_hbr
from py_hbr.clinical_codes import get_codes_in_group, ClinicalCodeParser
import code_group_counts as codes
import datetime as dt
import sparse_encode as spe

import hes

importlib.reload(hes)
importlib.reload(codes)
importlib.reload(py_hbr)
importlib.reload(spe)

# Get raw data
start_date = dt.date(2023,1,1)
end_date = dt.date(2023,2,1)
raw_data = hes.get_spells_hes_pandas(start_date, end_date)

# Reduce the data to a size UMAP can handle.
# Copy in order to not modify raw_data (to use
# inplace=True later). Want to keep the raw
# data to avoid SQL fetch time.
#reduced = raw_data.head(50000).copy()
reduced = raw_data.copy()

# Remove irrelevant columns
cols_to_remove = ["nhs_number", "spell_start_date", "spell_end_date"]
reduced.drop(columns=cols_to_remove, axis=1, inplace=True)

# Replace all empty strings in the table with NA
reduced.replace("", np.nan, inplace=True)

# Extract the demographic information for use later.
age_and_gender = reduced[["spell_id", "age", "gender"]].copy()

# Convert the wide codes to long format in place
reduced = hes.convert_codes_to_long(reduced)

# The same spell can have the same diagnosis or procedure code in
# multiple positions. Keep onlt the highest priority code (the one
# with the lowest code position). This might arise due to aggregating
# the spells from underlying episodes, depending on the method that
# was used.
reduced = reduced.groupby(["spell_id", "full_code"]).min().reset_index()

# Map the position onto the following linear scale: primary diagnosis
# is 24, through secondary_diagnosis_23 is 1 (same for procedure). The
# intention is to later create a linear scale where a higher number
# means a higher priority diagnosis or procedure, and the value 0 is
# reserved for diagnosis or procedure not present
reduced = hes.make_linear_position_scale(reduced, 23)

# Trying to keep all the codes as individual columns and using
# all the spells results in much more data than than pandas can
# handle (attempting to pivot wider), without writing a custom
# encoder. One approach is to only keep columns for the most
# commonly occurring codes. However, doing this results in some
# kind of degenerate UMAP result, which might result from the
# introduction of many spells with all-zero rows (i.e. no codes
# from the most commonly occurring group). If you see UMAP reduce
# the data to a set of roughly uniformly distributed points inside
# a circle in R2, this kind of issue is a likely culprit. Instead
# of doing this, the current script keeps all the code columns,
# and instead reduces the amount of spells so that the algorithm
# can cope. This is a prototype which can be extended (with more
# high performance code) later if it is worthwhile to do so.

# This line takes a long time to run, so make copies and modify them. This
# array has values that are ordered the same as the final embedding
dummy_encoded = pd.get_dummies(reduced, columns=["full_code"]).groupby("spell_id").max()

dummy_data_to_reduce2, ordered_spells = spe.encode_sparse(reduced)

# Get just the columns that will be dimension-reduced
dummy_data_to_reduce = dummy_encoded.filter(regex="(icd10|opcs4)")
dummy_data_to_reduce = scipy.sparse.csr_matrix(dummy_data_to_reduce.values)

# Get the age column in the same order as the data to reduce
dummy_ordered_age = dummy_encoded.merge(age_and_gender, on="spell_id").age

code_groups = codes.get_code_groups("../codes_files/icd10.yaml", "../codes_files/opcs4.yaml")

# ... get other values to plot on embedding here
def get_code_group_labels(reduced, code_group):
    group = get_codes_in_group("../codes_files/opcs4.yaml", code_group)
    group = "icd10_" + group.name.apply(hes.normalise_code)
    df = reduced.copy()
    df["ingroup"] = df.full_code.isin(group)
    group = df.groupby("spell_id").ingroup.any()
    return dummy_encoded.merge(group, on="spell_id").ingroup


def get_ordered_group_labels(reduced, groups, code_groups):
    """
    Get a dataframe of spell_id with a column indicating whether
    each spell has a code from a set of groups. The column 'label'
    contains a group name from groups if the spell has a code from
    those groups. If a spell contains codes from multiple of these
    groups, then only the first one is recorded (so the order of the
    groups list matter -- items at the front are higher priority).
    """
    # Get a list of the relevant codes (the ones in groups), along
    # with the name in the format of the reduced dataframe
    relevant_codes = code_groups[code_groups["group"].isin(groups)].copy()
    icd10_or_opcs4 = [
        "icd10_" if x == "diagnosis" else "opcs4_" for x in relevant_codes.type
    ]
    relevant_codes["full_code"] = icd10_or_opcs4 + relevant_codes["name"]
    relevant_codes = relevant_codes[["full_code", "group"]]

    reduced_with_groups = reduced.merge(relevant_codes, how="left", on="full_code")[
        ["spell_id", "group"]
    ].replace(np.nan, "none")
    reduced_with_groups.drop_duplicates(inplace=True)

    # The next line sorts the group according to the order of the
    # groups argument. First append "none" to the groups
    groups.append("none")
    reduced_with_groups.sort_values(
        by="group",
        key=lambda column: column.map(lambda e: groups.index(e)),
        inplace=True,
    )
    # Pick only the first group in each spell (now priority give by groups order)
    reduced_with_groups = reduced_with_groups.groupby("spell_id").first().reset_index()

    # reduced.groupby("spell_id").
    return reduced_with_groups

# Pivot to keep the diagnosis position as the value of the code,
# instead of just a TRUE/FALSE. The value after this pivot is the
# linear diagnosis/procedure scale from 1 (last secondary) to 24
# (primary); replace NA with 0 to indicate no code present.
linear_encoded = reduced.pivot(
    index="spell_id", columns="full_code", values="position"
).fillna(0)

# Get just the columns that will be dimension-reduced
linear_data_to_reduce = linear_encoded.filter(regex="(icd10|opcs4)")
linear_data_to_reduce = scipy.sparse.csr_matrix(linear_data_to_reduce.values)

# Get the age column in the same order as the data to reduce
linear_ordered_age = linear_encoded.merge(age_and_gender, on="spell_id").age
# ... get other values to plot on embedding here

# UMAP has the following parameters:
#
# - n_neighbors: this is the number of nearest neighbors to
#   use in the approximation of a uniform distance around
#   each data point in the original manifold. Choosing a
#   a large number will course-grain the manifold, so that
#   the uniform distances are approximated over larger groups
#   of spells.
# - min_dist: in the dimension-reduced manifold (after projection
#   from the original manifold), the local-connectedness condition
#   which translated to assuming that each data point is 0 distance
#   away from its nearest neighbour, must translate to an arbitrary
#   choice for what this minimum distance is in the Euclidean plane.
#   Making it small will cause more clustering, whereas making it
#   large will push points away from each other, which may focus
#   more on the overall topological structure.
# - n_components: the n here is the dimension of the reduced space,
#   which is the manifold R^n with the standard topology arising
#   from Eucliean distances
# - metric: which metric is used to measure distance between the
#   different points of the dataset in the original (ambient)
#   space R^m (m is the number of columns in the original dataset).
#   Here, there is one binary column per clinical code, and two rows
#   (spells) are considered different according to how many of their
#   clinical codes differ -- this is the Hamming distance.

dummy_mapper = umap.UMAP(metric="hamming", random_state=1, verbose=True)
embedding = dummy_mapper.fit_transform(dummy_data_to_reduce)

mapper3 = umap.UMAP(metric="hamming", random_state=1, verbose=True, n_components = 3)
embedding3 = mapper3.fit_transform(dummy_data_to_reduce)

# Helper for plotting distributions (3D)
def plot_discrete_groups(embedding, reduced, groups, colour_map, title):
    ordered_groups = get_ordered_group_labels(reduced, groups, code_groups)
    fig, ax = plt.subplots(projection = "3d")
    for g in ordered_groups.group.unique():
        ix = np.where(ordered_groups.group == g)
        ax.scatter(
            embedding[ix, 2], embedding[ix, 1], embedding[ix, 0], marker=".", s=10, c=colour_map[g], label=g
        )
    plt.title(title, fontsize=24)
    plt.legend()
    plt.show()

# Helper for plotting distributions
def plot_discrete_groups(embedding, reduced, groups, colour_map, title):
    ordered_groups = get_ordered_group_labels(reduced, groups, code_groups)
    fig = plt.figure() 
    ax = fig.add_subplot()
    for g in ordered_groups.group.unique():
        ix = np.where(ordered_groups.group == g)
        ax.scatter(
            embedding[ix, 1], embedding[ix, 0], marker=".", s=10, c=colour_map[g], label=g
        )
    plt.title(title, fontsize=24)
    plt.legend()
    plt.show()

code_parser = ClinicalCodeParser("../codes_files/icd10.yaml", "../codes_files/opcs4.yaml")

# Plot basic embedding###################
# fig = plt.figure()
# ax = fig.add_subplot()
# ax.scatter(
#     embedding[:, 1], embedding[:, 0], marker=".", s=5,
#     picker = True
#     )
# plt.title(f"{embedding.shape[0]} Spells, {dummy_data_to_reduce.shape[1]} Code Dimensions (one per ICD-10/OPCS-4)", fontsize=24)
fig, ax = plt.subplots()
points = ax.scatter(
    embedding[:, 1], embedding[:, 0], marker=".", s=5, c=dummy_ordered_age, picker=True
)
fig.colorbar(points, label="Age")
plt.title("Age Distribution", fontsize=24)

def parse_code(code, diagnosis_or_procedure):
    try:
        return code_parser.find_exact(code, diagnosis_or_procedure).docs
    except:
        return f"Invalid {diagnosis_or_procedure} code {code}"

def onpick(event):
    # Can return a list if multiple points are clicked
    ind = event.ind
    spells = [dummy_encoded.index[n] for n in ind]
    print(f"Clicked {len(ind)} points")
    codes = reduced[reduced.spell_id.isin(spells)]["full_code"].value_counts().reset_index().head(20)

    codes[["diagnosis_or_procedure", "code"]] = codes["full_code"].str.split("_", expand = True)
    codes["diagnosis_or_procedure"] = codes["diagnosis_or_procedure"].map({"icd10": "diagnosis", "opcs4": "procedure"})
    codes["docs"] = codes.apply(lambda x: parse_code(x["code"], x["diagnosis_or_procedure"]), axis=1)
    fig, ax = plt.subplots()

    colour_map = {"diagnosis": "b", "procedure": "r"}
    print(codes)
    ax.barh(codes.index, codes["count"], color = codes["diagnosis_or_procedure"].map(colour_map), align='center')
    ax.set_yticks(codes.index, labels=codes["docs"])
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('Count')
    ax.set_title('Total codes seen at this point')
    plt.subplots_adjust(left=0.50)
    plt.show()

fig.canvas.mpl_connect('pick_event', onpick)

plt.show()

########################

# Plot PCI
colour_map = {"pci": "r", "none": "lightgray"}
plot_discrete_groups(
    embedding,
    reduced,
    ["pci"],
    colour_map,
    "Distribution of PCI",
)

# Plot STEMI/NSTEMI
colour_map = {"mi_stemi_schnier": "r", "mi_nstemi_schnier": "b", "none": "lightgray"}
plot_discrete_groups(
    embedding,
    reduced,
    ["mi_nstemi_schnier", "mi_stemi_schnier"],
    colour_map,
    "Distribution of STEMI/NSTEMI MI",
)

# Plot bleeding
colour_map = {"bleeding_al_ani": "r", "none": "lightgray"}
plot_discrete_groups(
    embedding,
    reduced,
    ["bleeding_al_ani"],
    colour_map,
    "Distribution of Bleeding",
)

# Plot CKD
colour_map = {"ckd": "r", "none": "lightgray"}
plot_discrete_groups(
    embedding,
    reduced,
    ["ckd"],
    colour_map,
    "Distribution of CKD",
)

# Plot diabetes
colour_map = {"diabetes_type1": "r", "diabetes_type2": "b", "none": "lightgray"}
plot_discrete_groups(
    embedding,
    reduced,
    ["diabetes_type1", "diabetes_type2"],
    colour_map,
    "Distribution of Type1/Type2 diabetes",
)

# Plot cancer
colour_map = {"cancer": "r", "none": "lightgray"}
plot_discrete_groups(
    embedding,
    reduced,
    ["cancer"],
    colour_map,
    "Distribution of Cancer (all neoplasms)",
)

# Plot age on reduction
fig, ax = plt.subplots()
points = ax.scatter(
    embedding[:, 1], embedding[:, 0], marker=".", s=5, c=dummy_ordered_age
)
fig.colorbar(points, label="Age")
plt.title("Age Distribution", fontsize=24)
plt.show()








###########################

linear_mapper = umap.UMAP(metric="euclidean", random_state=3, verbose=True)
linear_fit = linear_mapper.fit(linear_data_to_reduce)
# umap.plot.diagnostic(dummy_fit, diagnostic_type='local_dim')
umap.plot.points(linear_fit, values=linear_ordered_age, theme="viridis")
plt.show()

embedding = mapper.fit_transform(encoded)
plt.scatter(embedding[:, 0], embedding[:, 1])
plt.gca().set_aspect("equal", "datalim")
plt.title("UMAP projection of HES spell codes", fontsize=24)
plt.show()

# 2D embedding
fit = umap.UMAP(
    n_neighbors=50,
    min_dist=0.1,
    n_components=2,
    # metric = "euclidean"
)
data_to_reduce = full_encoded.filter(
    regex="(icd10|opcs4)"
)  # Use "full_code" for dummy encoding
embedding2d = fit.fit_transform(data_to_reduce)
embedding2d.shape
plt.scatter(embedding2d[:, 0], embedding2d[:, 1], c=full_encoded["age"])
plt.gca().set_aspect("equal", "datalim")
plt.title("UMAP projection of HES spell codes", fontsize=24)
plt.show()

embedding_old = embedding2d

# Apply UMAP to reduce to 3 dimensions
fit = umap.UMAP(n_neighbors=15, min_dist=0.1, n_components=3, metric="hamming")
embedding3d = fit.fit_transform(full_encoded)
embedding3d.shape

# 3D embedding
fig = plt.figure()
ax = fig.add_subplot(projection="3d")
ax.scatter(embedding3d[:, 0], embedding3d[:, 1], embedding3d[:, 2])
plt.gca().set_aspect("equal", "datalim")
plt.title("UMAP projection of HES spell codes", fontsize=24)
plt.show()
