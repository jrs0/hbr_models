# UMAP Experiment
#
# The purpose of this experiment is to test whether dimension
# reduction of HES diagnosis/procedure codes can produce good
# bleeding risk predictions, compared to using manually-chose
# code groups.

import os

os.chdir("scripts/prototypes")

from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_curve, roc_auc_score
import numpy as np
import save_datasets as ds
import matplotlib.pyplot as plt
import umap
import umap.plot
import pandas as pd
import seaborn as sns

sns.set(style="ticks")
from functools import reduce

# 0. Prepare the datasets

# Use the manual_codes table above to create a new table
# dropping unneeded columns

# Create/save/load the manual code groups dataset
# - 16 code group predictors (manually chosen groups)
# - age, gender, stemi, nstemi, pci predictors
# - outcome: bleeding_al_ani_outcome
# - index: idx_episode_id
# data_manual = manual_codes.filter(regex=("(before|age|gender|stemi|pci|bleeding_al_ani_outcome)"))
# ds.save_dataset(data_manual, "data_manual")
data_manual = ds.load_dataset("data_manual", True)

# Create/save/load the UMAP all-codes dataset
# base_info = idx_episodes.filter(regex="(episode_id|age|gender|stemi|pci)")
# base_info.set_index("idx_episode_id", inplace=True)
# feature_any_code.set_index("idx_episode_id", inplace=True)
# predictors = pd.merge(base_info, feature_any_code, on="idx_episode_id")
# del feature_any_code # If you are short on memory
# outcomes = outcome_counts[["idx_episode_id","bleeding_al_ani_outcome"]].set_index("idx_episode_id")
# data_umap = pd.merge(predictors, outcomes, on="idx_episode_id")
# del predictors
# ds.save_dataset(data_umap, "data_umap")
data_umap = ds.load_dataset("data_umap", True)

# 1. Get a set of index events

# The index events are ACS/PCI patients. This table is the
# data_manual dataframe above, which also contains the manual
# diagnosis/procedure group columns as predictors.
#
# Split this data into a test and a training set -- the idea
# is that no data from the set used to test the models leaks
# into the data used to fit the UMAP reduction (or the model
# fits either).

# First, get the outcomes (y) from the dataframe. This is the
# source of test/train outcome data, and is used for both the
# manual and UMAP models. Just interested in whether bleeding
# occurred (not number of occurrences) for this experiment
outcome_name = "bleeding_al_ani_outcome"
y = data_manual[outcome_name]

# Get the set of manual code predictors (X0) to use for the
# first logistic regression model (all the columns with names
# ending in "_before").
X0 = data_manual.drop(columns=[outcome_name])

rng = np.random.RandomState(0)

# Make a random test/train split.
test_set_proportion = 0.25
X0_train, X0_test, y_train, y_test = train_test_split(
    X0, y, test_size=test_set_proportion, random_state=rng
)

# 2. Fit logistic regression in the training set using code groups


def make_reducer_wrapper(reducer, cols_to_reduce: list[str]) -> ColumnTransformer:
    """Make a wrapper that applies dimension reduction.

    Args:
        reducer: The dimension reduction model to use for reduction
        cols_to_reduce: The list of column names to reduce

    Returns:
        The column transformer that applies the dimension reducer
            to the columns listed.
    """
    return ColumnTransformer(
        [("reducer", umapper, reduce_cols)],
        remainder="passthrough",
        verbose_feature_names_out=True,
    )


def make_logistic_regression(random_state) -> list:
    """Make a new logistic regression model

    The model involves scaling all predictors and then
    applying a logistic regression model.

    Returns:
        A list of tuples suitable for passing to the
            scikit learn Pipeline.
    """

    scaler = StandardScaler()
    logreg = LogisticRegression(verbose=3, random_state=random_state)
    model = [("scaler", scaler), ("model", logreg)]
    return model


def make_pipe(model: list, reducer: ColumnTransformer = None) -> Pipeline:
    """Make a model pipeline from the model part and dimension reduction

    This function can be used to make the pipeline with no dimension
    (pass None to reducer). Otherwise, pass the reducer which will reduce
    a subset of the columns before fitting the model.

    Args:
        model: A list of model fitting steps that should be applied
            after the (optional) dimension reduction.
        reducer: If non-None, this reduction (which applies only to the
            subset of columns listed in the ColumnTransformer -- other
            columns are passed-through)

    Returns:
        A scikit-learn pipeline that can be fitted to training data.
    """
    if reducer is not None:
        reducer_part = [("reducer", reducer)]
        pipe = Pipeline(reducer_part + model)
    else:
        pipe = Pipeline(model)
    return pipe


# The pipe used to assess the model performance using
# manually chosen code groups
baseline_pipe = make_pipe(make_logistic_regression(rng))

# Fit the baseline pipe (manual code groups)
baseline_fit = baseline_pipe.fit(X0_train, y_train)

# Test the baseline performance on the test set and
# get ROC AUC
baseline_probs = baseline_fit.predict_proba(X0_test.filter(regex=".*"))[:, 1]
baseline_auc = roc_auc_score(y_test, baseline_probs)
baseline_auc

# 3. Fit the dimension reduced model

# Dimension reduce model and columns to reduce
umapper = umap.UMAP(metric="hamming", n_components=3, random_state=rng, verbose=True)
cols_to_reduce = [c for c in X1_train.columns if ("diag" in c) or ("proc" in c)]

# The pipe used to perform dimension reduction the fit the model
reducer_wrapper = make_reducer_wrapper(umapper, cols_to_reduce)
reduce_pipe = make_pipe(make_logistic_regression(rng), reducer_wrapper)

# Fit the dimension reduction pipe
reduce_fit = reduce_pipe.fit(X1_train, y_train)

# Test the performance including dimension reduction and get the
# ROC AUC
reduce_probs = reduce_fit.predict_proba(X1_test.filter(regex=".*"))[:, 1]
reduce_auc = roc_auc_score(y_test, reduce_probs)
reduce_auc








model0 = RandomForestClassifier(
    verbose=3, n_estimators=100, max_depth=10, random_state=rng
)


pipe0 = Pipeline(
    [
        # ("scaler", scaler0),
        ("model", model0),
    ]
)
fit0 = pipe0.fit(X0_train.filter(regex=".*"), y_train)

# Get variable importance for random forest
var_importance0 = pd.DataFrame(
    {"Var": X0_train.columns, "Coeff": fit0["model"].feature_importances_.tolist()}
).sort_values("Coeff")

# Get the top predictors for logistic regression
# var_importance0 = pd.DataFrame(
#     {"Var": X0_train.columns, "Coeff": fit0["logreg"].coef_.tolist()[0]}
# ).sort_values("Coeff")

# Fit to the test set and look at ROC AUC


# 3. Dimension-reduce the diagnosis/procedures using UMAP

# In this step, take all the patients in the training set, and
# find all the diagnosis/procedure codes tha appeared in the
# year before index (give one bool column-per-code -- could count
# the number of codes, but don't want to bias it in case the
# count is actually irrelevant (e.g. a common code might not be
# an important one).
#
# That gives a table with one row per index event, and lots of
# columns (one per code)
#
# Perform UMAP to reduce this to a table with the same number
# of predictor columns as there were manual code groups (to see
# if UMAP does a better job at picking the same number of
# predictors)
#

# First, extract the test/train sets from the UMAP data based on
# the index of the training set for the manual codes
X1_train = data_umap.loc[X0_train.index]
X1_test = data_umap.loc[X0_test.index]

# We will train a UMAP reduction on the X1_train table diagnosis/
# procedure columns, then manually apply this to the training set.
code_cols_train = X1_train.filter(regex=("diag|proc"))

mapper = umap.UMAP(metric="hamming", n_components=4, random_state=rng, verbose=True)

# Fit UMAP to the training set -- this fit is then also used
# to perform the same step on the test set later (so cannot use
# fit_transform)
umap_fit = mapper.fit(code_cols_train)

# Apply the fit to the training data to get the embedding
emb_train = umap_fit.transform(code_cols_train)

# Insert these columns back into the X1_train data frame in
# place of the original diagnosis/procedure code columns.
# The result is the input data for fitting logistic regression
reduced_dims = pd.DataFrame(emb_train)
reduced_dims.columns = [f"f{n}" for n in range(reduced_dims.shape[1])]
reduced_dims.index = X1_train.index
X1_train_reduced = pd.merge(
    X1_train.filter(regex="age|gender|idx"), reduced_dims, on="idx_episode_id"
)

# ==================== For Plotting 2D =====================

# To use this bit, ensure that the the ncomponents is set to
# 2 (to be able to plot it).

import code_group_counts as cgc

code_groups_df = cgc.get_code_groups(
    "../codes_files/icd10.yaml", "../codes_files/opcs4.yaml"
)


def code_counts_in_row(group, group_name, code_groups, X1_train):
    # Flag all the codes in a group
    groups = code_groups[code_groups["group"] == group]["name"]
    group_regex = "|".join(groups.to_list())
    code_counts = X1_train.filter(regex=group_regex).sum(axis=1)
    code_counts.name = group_name
    return code_counts


groups_map = {
    "bleeding_al_ani": "Prior Bleeding",
    "acs_bezin": "Prior ACS",
    "pci": "Prior PCI",
    "ckd": "CKD",
    "cancer": "Cancer",
    "diabetes": "Diabetes",
}


def get_most_common_group(groups_map, code_groups, X1_train):
    dfs = [
        code_counts_in_row(g, n, code_groups, X1_train) for g, n in groups_map.items()
    ]
    full = reduce(lambda left, right: pd.merge(left, right, on="idx_episode_id"), dfs)
    full["None"] = 0.1  # trick to make idxmax identify where row has no code
    return full.astype(float).idxmax(axis=1)


# Plot a particular code group
X1_train_embedding = pd.DataFrame(emb_train).set_index(X1_train.index)
X1_train_embedding["Group"] = get_most_common_group(
    groups_map, code_groups_df, X1_train
)
X1_train_embedding.columns = ["Feature 1", "Feature 2", "Group"]
# palette = sns.color_palette("rocket")
sns.set(font_scale=1.2)
plt.rcParams["legend.markerscale"] = 5
sns.set_theme(style="white", palette=None)
sns.relplot(
    data=X1_train_embedding, x="Feature 1", y="Feature 2", hue="Group", marker=".", s=15
)
plt.title(f"Distribution of Code Groups")
plt.show()

# Plot age on the graph
X1_train_embedding = pd.DataFrame(emb_train).set_index(X1_train.index)
X1_train_embedding["Age"] = X1_train["dem_age"]
X1_train_embedding.columns = ["Feature 1", "Feature 2", "Age"]
sns.relplot(data=X1_train_embedding, x="Feature 1", y="Feature 2", hue="Age", s=15)
plt.title(f"Distribution of Age")
plt.show()

# ================ For Plotting 3D ==================

# Plot a particular code group
X1_train_embedding = pd.DataFrame(emb_train).set_index(X1_train.index)
X1_train_embedding["Group"] = get_most_common_group(
    groups_map, code_groups_df, X1_train
)
X1_train_embedding.columns = ["Feature 1", "Feature 2", "Feature 3", "Group"]

fig = plt.figure()
ax = fig.add_subplot(111, projection="3d")

# Rename for simplicity
df = X1_train_embedding
for s in df.Group.unique():
    ax.scatter(
        df["Feature 1"][df["Group"] == s],
        df["Feature 2"][df["Group"] == s],
        df["Feature 3"][df["Group"] == s],
        label=s,
        marker=".",
        s=1,
    )

ax.set_xlabel("Feature 1")
ax.set_ylabel("Feature 2")
ax.set_zlabel("Feature 3")
ax.legend()
plt.show()

# ================ End of plotting ==================


# 4. Fit a log. reg. on the UMAP-predictor table

# model1 = LogisticRegression(verbose=0, random_state=rng)
model1 = RandomForestClassifier(
    verbose=3, n_estimators=100, max_depth=5, random_state=rng
)
scaler1 = StandardScaler()

pipe1 = Pipeline(
    [
        # ("scaler", scaler1),
        ("model", model1),
    ]
)
fit1 = pipe1.fit(X1_train_reduced, y_train)

# Get variable importance for random forest
var_importance1 = pd.DataFrame(
    {
        "Var": X1_train_reduced.columns,
        "Coeff": fit1["model"].feature_importances_.tolist(),
    }
).sort_values("Coeff")

# Get the top predictors for this model
# var_importance1 = pd.DataFrame(
#    {"Var": X1_train_reduced.columns, "Coeff": fit1["logreg"].coef_.tolist()[0]}
# ).sort_values("Coeff")

# Run the model on the test set

# To predict probabilities for the UMAP logistic
# regression, it is first necessary to reduce the
# test set using the fitted UMAP
code_cols_test = X1_test.filter(regex=("diag|proc"))
emb_test = umap_fit.transform(code_cols_test)
reduced_dims = pd.DataFrame(emb_test)
reduced_dims.columns = [f"f{n}" for n in range(reduced_dims.shape[1])]
reduced_dims.index = X1_test.index
X1_test_reduced = pd.merge(
    X1_test.filter(regex="age|gender|idx"), reduced_dims, on="idx_episode_id"
)

# Predict probabilities for UMAP model
probs1 = fit1.predict_proba(X1_test_reduced)[:, 1]
auc1 = roc_auc_score(y_test, probs1)
auc1

# 5. Test both models on the test set

# Want to plot the ROC curve and get the ROC AUC. In a next
# step, want to do some stability analysis for this whole
# process.
#

fpr0, tpr0, _ = roc_curve(y_test, probs0)
roc0 = pd.DataFrame(
    {
        "False positive rate": fpr0,
        "True positive rate": tpr0,
        "Model": f"Manual Groups (AUC = {auc0:0.2f})",
    }
)


fpr1, tpr1, _ = roc_curve(y_test, probs1)
roc1 = pd.DataFrame(
    {
        "False positive rate": fpr1,
        "True positive rate": tpr1,
        "Model": f"UMAP (AUC = {auc1:0.2f})",
    }
)


# Plot the ROC curves for both models
roc = pd.concat([roc0, roc1])
g = sns.lineplot(
    data=roc,
    x="False positive rate",
    y="True positive rate",
    hue="Model",
    errorbar=None,
)
sns.move_legend(g, "lower right")
plt.title(f"ROC Curve for Each Model")
plt.plot([0, 1], [0, 1])
plt.show()
