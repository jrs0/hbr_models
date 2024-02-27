# UMAP Experiment
#
# The purpose of this experiment is to test whether dimension
# reduction of HES diagnosis/procedure codes can produce good
# bleeding risk predictions, compared to using manually-chose
# code groups.

import os

os.chdir("scripts/prototypes")

from sklearn.compose import ColumnTransformer
from sklearn.decomposition import TruncatedSVD
from sklearn.random_projection import GaussianRandomProjection
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
from typing import Callable
from pandas import DataFrame
from numpy.random import RandomState
from numpy import ndarray

from code_group_counts import get_code_groups
from pandas import Series


def make_column_transformer(reducer, cols_to_reduce: list[str]) -> ColumnTransformer:
    """Make a wrapper that applies dimension reduction to a subset of columns.

    Args:
        reducer: The dimension reduction model to use for reduction
        cols_to_reduce: The list of column names to reduce

    Returns:
        The column transformer that applies the dimension reducer
            to the columns listed.
    """
    return ColumnTransformer(
        [("reducer", reducer, cols_to_reduce)],
        remainder="passthrough",
        verbose_feature_names_out=True,
    )


def make_pipe(model: list, column_transformer: ColumnTransformer = None) -> Pipeline:
    """Make a model pipeline from the model part and dimension reduction

    This function can be used to make the pipeline with no dimension
    (pass None to reducer). Otherwise, pass the reducer which will reduce
    a subset of the columns before fitting the model.

    Args:
        model: A list of model fitting steps that should be applied
            after the (optional) dimension reduction.
        column_transformer: If non-None, this reduction (which applies only to the
            subset of columns listed in the ColumnTransformer -- other
            columns are passed-through)

    Returns:
        A scikit-learn pipeline that can be fitted to training data.
    """
    if column_transformer is not None:
        reducer_part = [("column_transformer", column_transformer)]
        pipe = Pipeline(reducer_part + model)
    else:
        pipe = Pipeline(model)
    return pipe


def logistic_regression_coefficients(fitted_model: LogisticRegression) -> list[float]:
    """Return the list of logistic regression variable coefficients.

    Used to make an assessment of which features have the biggest influence
    on the output class.

    Note: Using logistic regression coefficients for feature importance is not
    necessarily the right thing to do. Consider replacing this function with another
    in the call to baseline_feature_importance.

    Args:
        fitted_model: The logistic regression model after it has been fitted
            to the training data
    """
    return fitted_model.coef_[0]


def baseline_feature_importance(
    fitted_pipe: Pipeline, importance_calc: Callable
) -> DataFrame:
    """Get a table of the feature importances in the baseline model

    This function takes a pipeline which assumes that all variables are used in the final
    model (and the column order is not changed), and a function that calculates
    the feature importances from the final step in the pipeline (assumed to be called
    "model").

    Args:
        fitted_pipe: Fitted pipeline which does not reduce columns and maintains the order
           of features. Used to get feature names.
        importance_calc: A function to convert fitted_pipe["model"] (the final step) into a
           list of feature importances, which will be paired with the column names.

    Returns:
        The feature importances of each column input in the baseline model (no dimension reduction)
    """
    fitted_model = fitted_pipe["model"]
    var_importances = importance_calc(fitted_model)
    var_names = fitted_pipe.feature_names_in_
    df = pd.DataFrame(
        {
            "Feature": var_names,
            "Importance": var_importances,
        }
    ).sort_values(
        "Importance"
    )  # Replace with order by magnitude
    return df


def reduce_feature_importance(
    fitted_pipe: Pipeline, importance_calc: Callable
) -> DataFrame:
    """Get a table of the feature importances in the dim-reduce model"""
    fitted_model = fitted_pipe["model"]
    var_importances = importance_calc(fitted_model)
    var_names = post_reduce_features(fitted_pipe)
    df = pd.DataFrame(
        {
            "Feature": var_names,
            "Importance": var_importances,
        }
    ).sort_values(
        "Importance"
    )  # Replace with order by magnitude
    return df


def post_reduce_features(fitted_pipe: Pipeline) -> list[str]:
    """Get the list of variables after dimension reduction.

    This function accounts for the re-ordering of variables that is performed
    by the column transformer (reduced dimensions are placed at the front).

    Args:
        fitted_pipe: The fitted pipeline object, containing a ColumnTransformer
            called "column_transformer" as the first step, which contains a
            "reducer" that processes cols_to_reduce (other columns are passed
            through).

    Returns:
        The feature names in the final training set, after dimension reduction and
            before modelling.
    """

    # Get the column transformer and reducer
    column_transformer = fitted_pipe["column_transformer"]
    reducer = column_transformer.named_transformers_["reducer"]

    # Get the columns being reduced from the ColumnTransformer
    for transformer in column_transformer.transformers:
        if transformer[0] == "reducer":
            # Extract the list of columns to process from the tuple
            cols_to_reduce = transformer[2]
            break

    # Get all input features (before reduction)
    input_vars = reduce_fit["column_transformer"].feature_names_in_

    # Make the lsit of variables which are not processed
    remainder_vars = [col for col in input_vars if col not in cols_to_reduce]

    # Reducer is processed first, so the reduced columns come at the front
    # of the dataframe
    reduce_vars = list(
        reduce_fit["column_transformer"]
        .named_transformers_["reducer"]
        .get_feature_names_out()
    )

    # Append the remainder vars to get all the variables in the final dataframe
    all_vars = reduce_vars + remainder_vars

    return all_vars


def prepare_test_train(
    data_manual: DataFrame, data_reduce: DataFrame, rng: RandomState
) -> (DataFrame, DataFrame, DataFrame, DataFrame):
    """Make the test/train datasets for manually-chosen groups and high-dimensional data

    Args:
        data_manual: The dataset with manually-chosen code groups
        data_reduce: The high-dimensional dataset
        rng: The random state to pick the test/train split

    Returns:
        A tuple (y_train, y_test, X0_train, X0_test, X1_train, X1_test),
            where the index 0 refers to the manual code groups data and
            1 refers to the high-dimensional data.
    """

    # Check number of rows match
    if data_manual.shape[0] != data_reduce.shape[0]:
        raise RuntimeError(
            "The number of rows in data_manual and data_reduce do not match."
        )

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

    # Make a random test/train split.
    test_set_proportion = 0.25
    X0_train, X0_test, y_train, y_test = train_test_split(
        X0, y, test_size=test_set_proportion, random_state=rng
    )

    # Extract the test/train sets from the UMAP data based on
    # the index of the training set for the manual codes
    X1 = data_reduce.drop(columns=[outcome_name])
    X1_train = X1.loc[X0_train.index]
    X1_test = X1.loc[X0_test.index]

    return y_train, y_test, X0_train, X0_test, X1_train, X1_test


def predict_probabilities(fitted_pipe: Pipeline, X_test: DataFrame) -> ndarray:
    """Predict probabilities of a positive outcome for each row of the test set

    Args:
        fitted_pipe: The fit returned from fit_model()
        X_test: The test dataset on which to make the predictions

    Returns:
        An array of probabilities

    """
    return fitted_pipe.predict_proba(X_test)[:, 1]


def fit_model(
    random_state: RandomState,
    y_train: DataFrame,
    X_train: DataFrame,
    model_maker: Callable,
    reducer_maker: Callable | None = None,
) -> Pipeline:
    """Create and fit a model, optionally with dimension reduction first

    Args:
        random_state: The random state to use for functions that require randomness
        model_maker: Function to create the model to use after (optional) dimension reduction
        reducer_maker: Function to use to make the dimension reducer. If None is passed, no
           dimension reduction will be performed

    Returns:
        The fitted pipeline after applying dimension reduction (if reducer_maker not None)
    """
    reducer_wrapper = None
    if reducer_maker is not None:
        # The columns that need dimension reduction are those starting diagnosis_
        # or procedure_
        cols_to_reduce = [c for c in X_train.columns if ("diag" in c) or ("proc" in c)]
        reducer = reducer_maker(random_state)
        reducer_wrapper = make_column_transformer(reducer, cols_to_reduce)

    # The pipe used to assess the model performance using
    # manually chosen code groups
    pipe = make_pipe(model_maker(random_state), reducer_wrapper)

    # Fit the baseline pipe (manual code groups)
    return pipe.fit(X_train, y_train)


# 0. Prepare the datasets

# Load both datasets
data_manual = ds.load_dataset("data_manual", True)
data_reduce = ds.load_dataset("data_umap", True)

# 1. Test/train split

random_state = None  # RandomState(0)

# Make the test/train split for both datasets
y_train, y_test, X0_train, X0_test, X1_train, X1_test = prepare_test_train(
    data_manual, data_reduce, random_state
)

# 2. Fit logistic regression in the training set using code groups


def single_fit(
    random_state: RandomState,
    y_train: DataFrame,
    y_test: DataFrame,
    X0_train: DataFrame,
    X1_train: DataFrame,
    X0_test: DataFrame,
    X1_test: DataFrame,
    model_maker: Callable,
    reducer_maker: Callable,
):
    """Fit a single baseline and dimension-reduced model.

    This function does not include any stability analysis/bootstrapped fitting.

    Args:
        random_state: Source of randomness
        y_train: Outcome training data
        y_test: Outcome test data
        X0_train: Training features for the baseline (manual-codes) model
        X1_train: Training features for the dimension reduction model
        X0_test: Test features for the baseline (manual-codes) model
        X1_test: Test features for the dimension reduction model
        model_maker: Function to make the model
        reducer_maker: Function to make the dimension reducer

    Returns:
        A tuple of the baseline model fit object, the dimension-reducted fit
            object, the baseline probabilities on the test set, the dimension
            reduced probabilities on the test set, and the ROC AUC for the
            baseline and dimension reduced test sets.
    """

    # Fit the baseline model and the version using dimension reduction
    baseline_fit = fit_model(random_state, y_train, X0_train, model_maker, None)
    reduce_fit = fit_model(random_state, y_train, X1_train, model_maker, reducer_maker)

    # Test the baseline performance on the test set and
    # get ROC AUC
    baseline_probs = predict_probabilities(baseline_fit, X0_test)
    baseline_auc = roc_auc_score(y_test, baseline_probs)

    # Test set for reduced model
    reduce_probs = predict_probabilities(reduce_fit, X1_test)
    reduce_auc = roc_auc_score(y_test, reduce_probs)

    print("Finished fitting and testing:")
    print(f"- Baseline AUC: {baseline_auc}")
    print(f"- Reduce AUC: {reduce_auc}")

    return (
        baseline_fit,
        reduce_fit,
        baseline_probs,
        reduce_probs,
        baseline_auc,
        reduce_auc,
    )


def make_logistic_regression(random_state: RandomState) -> list:
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


def make_random_forest(random_state: RandomState) -> list:
    """Make a new random forest model

    Returns:
        A list of tuples suitable for passing to the
            scikit learn Pipeline.
    """
    random_forest = RandomForestClassifier(
        verbose=3, n_estimators=100, max_depth=10, random_state=random_state
    )
    model = [("model", random_forest)]
    return model


def make_umap_reducer(random_state: RandomState) -> umap.UMAP:
    """Make a UMAP reducer for use as dimension reduction.

    Args:
        random_state: Source of randomness

    Returns:
        umap.UMAP: The reducer object
    """
    # Dimension reduce model and columns to reduce
    return umap.UMAP(
        metric="hamming", n_components=3, random_state=random_state, verbose=True
    )


def make_tsvd_reducer(random_state: RandomState) -> TruncatedSVD:
    return TruncatedSVD(random_state=random_state, n_components=3)


def make_grp_reducer(random_state: RandomState) -> GaussianRandomProjection:
    return GaussianRandomProjection(random_state=random_state, n_components=300)


baseline_fit, reduce_fit, baseline_probs, reduce_probs, baseline_auc, reduce_auc = (
    single_fit(
        random_state,
        y_train,
        y_test,
        X0_train,
        X1_train,
        X0_test,
        X1_test,
        make_logistic_regression,
        make_tsvd_reducer,
    )
)


def reduce_dimensions(fitted_pipe: Pipeline, data: DataFrame) -> DataFrame:
    """Apply a fitted model to the training set to get the intermediate dimension-reduced data

    Use this function to get the intermediate result after applying dimension reduction
    to the training data. The result is what is passed to the modelling step and can be
    used to assess how the dimension reduction behaved.

    Args:
        fitted_pipe: The fitted pipe containing the dimension reduction and model
        data: The (high-dimensional) training or test set which should be diemnsion-reduced

    Returns:
        The result of applying the dimension reduction to the data. Preserves all the
            non-reduced columns (which end up at the end)
    """
    raw_array = fitted_pipe["column_transformer"].transform(data)
    after_reduce = pd.DataFrame(raw_array)
    after_reduce.columns = post_reduce_features(fitted_pipe)
    after_reduce.index = data.index
    return after_reduce


code_groups = get_code_groups("../codes_files/icd10.yaml", "../codes_files/opcs4.yaml")


def code_counts_in_rows(group: str, code_groups: DataFrame, data: DataFrame) -> Series:
    """Reduce rows to a count of a particular code group in each row

    Args:
        group: The name of the code group to count
        code_groups: DataFrame mapping column `group` to a column called `name` which
            stores all the codes in that group
        data: Data containing many columns each corresponding to a single code (containing
            the `name` from the code_groups table as part of the column name).

    Returns:
        The result of adding up all the columns for codes in the code group specified.
    """
    groups = code_groups[code_groups["group"] == group]["name"]
    group_regex = "|".join(groups.to_list())
    code_counts = data.filter(regex=group_regex).sum(axis=1)
    return code_counts


def get_most_common_group(
    groups_map: dict, code_groups: DataFrame, data: DataFrame
) -> Series:
    """Identify which code group occurred most often in each row

    Args:
        groups_map: A map from the group name to the desired column name in the output data
            for that group.
        code_groups: A table mapping the group name in the `group` column to the clinical codes
            in that group (in the `name` column)
        data: A table with one column for each clinical code, where each column name contains
            the `name` in the code_groups table.

    Returns:
        A table with one column showing which was the most common code group in the row,
            or None if none of the code groups appeared in the row.
    """
    dfs = []
    for group, group_name in groups_map.items():
        code_counts = code_counts_in_row(group, code_groups, data)
        code_counts.name = group_name
        dfs.append(code_counts)

    full = reduce(lambda left, right: pd.merge(left, right, on="idx_episode_id"), dfs)
    full["None"] = 0.1  # trick to make idxmax identify where a row has no code
    most_common = full.astype(float).idxmax(axis=1)
    return most_common


groups_map = {
    "bleeding_al_ani": "Prior Bleeding",
    "acs_bezin": "Prior ACS",
    "pci": "Prior PCI",
    "ckd": "CKD",
    "cancer": "Cancer",
    "diabetes": "Diabetes",
}


def get_reduced_columns_only(after_reduce: DataFrame) -> DataFrame:
    """Keep only the dimension reduced columns of the reduced data.

    This removes age, gender, and index characteristics, and leaves
    only the columns that arise from dimension reducing the clinical
    code columns.

    Args:
        data: The data after dimension reduction

    Returns:
        Only the dimension-reduced columns of the data
    """
    return after_reduce.loc[
        :, ~after_reduce.columns.str.contains("age|gender|idx")
    ].copy()


def plot_reduced_components(
    before_reduce: DataFrame, after_reduce: DataFrame, groups_map: dict
):
    """Plot a 2D or 3D graph of the reduced dimensions, coloured by clinical code group

    Args:
        before_reduce: The high-dimensional data including all the clinical code columns. This
            is required to count the occurrences of code groups
        after_reduce: The state of the data after applying the dimension reduction
            algorithm.
        groups_map: A map from group name to a readable name that should appear on the plot.
    """

    if before_reduce.shape[0] != after_reduce.shape[0]:
        raise RuntimeError(
            "Datasets before/after dimension reduction must have the same number of rows"
        )

    # Drop the columns which are not part of the dimension reduction
    reduced_columns = get_reduced_columns_only(after_reduce)

    # Add the most common group for each row
    reduced_columns["Group"] = get_most_common_group(
        groups_map, code_groups, before_reduce
    )

    # Rename the reduced columns for plotting
    num_components = reduced_columns.shape[1] - 1
    new_component_names = [f"Feature {n+1}" for n in range(num_components)]
    reduced_columns.columns = new_component_names + ["Group"]

    plt.rcParams["legend.markerscale"] = 5
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")

    # Rename for simplicity (subsample for speed)
    df = reduced_columns#.sample(frac=0.05)
    
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


after_reduce = reduce_dimensions(reduce_fit, X1_train)

plot_reduced_components(X1_train, after_reduce, groups_map)

baseline_importance = baseline_feature_importance(
    baseline_fit, logistic_regression_coefficients
)

# 3. Fit the dimension reduced model


# Fit the dimension reduction pipe
reduce_fit = reduce_pipe.fit(X1_train, y_train)

# Test the performance including dimension reduction and get the
# ROC AUC
reduce_probs = reduce_fit.predict_proba(X1_test)[:, 1]
reduce_auc = roc_auc_score(y_test, reduce_probs)
reduce_auc


reduce_feature_importance(reduce_fit, logistic_regression_coefficients)


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

reduce_feature_importance()

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
