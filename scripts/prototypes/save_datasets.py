import time, git
import os
import pandas as pd
import yaml
import re
import pickle
from scipy.sparse import csr_matrix
import numpy as np


def current_commit():
    """
    Get the first 12 characters of the current commit,
    using the first repository found above the current
    working directory
    """
    repo = git.Repo(search_parent_directories=True)
    sha = repo.head.object.hexsha[0:11]
    return sha


def current_timestamp():
    """
    Get the current timestamp (since epoch) rounded
    to the nearest seconds.
    """
    return int(time.time())


def save_fit_info(model, name):
    """
    Save fitted model information for creating graphs
    of model goodness-of-fit. Accepts a dictionary
    containing at least "probs" (a 2D numpy array of model
    predicted probabilities on the test set), and a
    "y_test" (a 1D numpy array with the actual test values).
    Other model-specific information may also be stored.

    TODO: This function duplicates most of the process in
    save_dataset, and the two should be combined.
    """
    datasets_dir = "models"

    if not os.path.isdir(datasets_dir):
        print("Creating missing folder '{datasets_dir}' for storing dataset")
        os.mkdir(datasets_dir)

    # Make the file suffix out of the current git
    # commit hash and the current time
    filename = f"{name}_{current_commit()}_{current_timestamp()}.pkl"
    path = os.path.join(datasets_dir, filename)

    with open(path, "wb") as handle:
        pickle.dump(model, handle, protocol=pickle.HIGHEST_PROTOCOL)


def save_dataset(dataset, name):
    """
    Saves a pandas dataframe to a file in the datasets/
    folder, using a filename with the current timestamp
    and the current commit hash.
    """
    datasets_dir = "datasets"

    if not os.path.isdir(datasets_dir):
        print("Creating missing folder '{datasets_dir}' for storing dataset")
        os.mkdir(datasets_dir)

    # Make the file suffix out of the current git
    # commit hash and the current time
    filename = f"{name}_{current_commit()}_{current_timestamp()}.pkl"
    path = os.path.join(datasets_dir, filename)

    dataset.to_pickle(path)


def get_file_list(name, directory = "datasets"):
    """
    Get the list of files in the datasets/ folder matching
    name. Return the result as a table of file path, commit
    hash, and saved date. The table is sorted by timestamp,
    with the most recent file first.
    """
    # Check for missing datasets directory
    datasets_dir = directory

    if not os.path.isdir(datasets_dir):
        raise RuntimeError(
            f"Missing folder '{datasets_dir}'. Check your working directory."
        )

    # Read all the .pkl files in the directory
    files = pd.DataFrame({"path": os.listdir(datasets_dir)})

    # Identify the file name part. The horrible regex matches the 
    # expression _[commit_hash]_[timestamp].pkl. It is important to
    # match this part, because "anything" can happen in the name part
    # (including underscores and letters and numbers), so splitting on
    # _ would not work. The name can then be removed
    files["name"] = files["path"].str.replace(r"_([0-9]|[a-zA-Z])*_\d*\.pkl", "", regex=True)

    # Remove all the files whose name does not match, and drop
    # the name from the path
    files = files[files["name"] == name]
    if files.shape[0] == 0:
        raise ValueError(
            f"There is not dataset with the name '{name}' in the datasets directory"
        )
    files["commit_and_timestamp"] = files["path"].str.replace(name + "_", "")

    # Split the commit and timestamp up (note also the extension)
    try:
        files[["commit", "timestamp", "extension"]] = files[
            "commit_and_timestamp"
        ].str.split(r"_|\.", expand=True)
    except:
        raise RuntimeError(
            "Failed to parse files in the datasets folder. "
            "Ensure that all files have the correct format "
            "name_commit_timestamp.(rds|pkl), and "
            "remove any files not matching this "
            "poattern. TODO handle this error properly, "
            "see save_datasets.py."
        )

    # Pick the most recent file to read and return
    files["created_date"] = pd.to_datetime(files["timestamp"].astype(int), unit="s")
    recent_first = files.sort_values(by="timestamp", ascending=False).reset_index()[
        ["path", "commit", "created_date"]
    ]
    return recent_first

def pick_file_interactive(name):
    """
    Print a list of the datasets in the datasets/ folder, along
    with the date and time it was generated, and the commit hash,
    and let the user pick which dataset should be loaded interactively.
    The full filename of the resulting file is returned, which can
    then be read by the user.
    """

    # Check for missing datasets directory
    datasets_dir = "datasets"

    recent_first = get_file_list(name)
    print(recent_first)

    num_datasets = recent_first.shape[0]
    while True:
        try:
            raw_choice = input(f"Pick a dataset to load: [{0} - {num_datasets-1}]: ")
            choice = int(raw_choice)
        except:
            print(f"{raw_choice} is not valid; try again.")
            continue
        if choice < 0 or choice >= num_datasets:
            print(f"{choice} is not in range; try again.")
            continue
        break

    full_path = os.path.join(datasets_dir, recent_first.loc[choice, "path"])
    return full_path

def pick_most_recent_file(name):
    """
    Like pick_file_interactive, but automatically selects the most
    recent file in the datasets/ folder
    """
    datasets_dir = "datasets"
    recent_first = get_file_list(name)
    full_path = os.path.join(datasets_dir, recent_first.loc[0, "path"])
    return full_path

def load_dataset(name, interactive):
    """
    Load a dataset from the datasets/ folder by name,
    letting the user interactively pick between different
    timestamps and commits
    """
    if interactive:
        dataset_path = pick_file_interactive(name)
    else:
        dataset_path = pick_most_recent_file(name)
        
    print(f"Loading {dataset_path}")
    return pd.read_pickle(dataset_path)


def load_fit_info(name):
    """
    Load the most recent version of fit info (the
    one with the latest timestamp).
    """
    model_dir = "models"
    recent_first = get_file_list(name, model_dir)
    full_path = os.path.join(model_dir, recent_first.loc[0, "path"])

    # Read and return the fit info dictionary
    with open(full_path, "rb") as handle:
        return pickle.load(handle)


def match_feature_list(feature_columns, feature_groups):
    """
    Helper function to group feature columns into groups defined
    by regex patterns. feature_columns is the list of columns names
    to be matched, and feature_groups is a dictionary of group names
    to regex expressions. The result is a dictionary mapping group
    names to lists of feature columns. ValueError is raised if there
    are columns which are not contained in any group.
    """
    feature_group_lists = {}
    for group, regex in feature_groups.items():
        p = re.compile(regex)
        matching_columns = [s for s in feature_columns if p.search(s)]
        if len(matching_columns) > 0:
            feature_group_lists[group] = matching_columns
        # Drop the matched columns from the set
        feature_columns = list(set(feature_columns) - set(matching_columns))

    # Create the set of unmatched columns
    if len(feature_columns) > 0:
        raise ValueError(
            f"Features {feature_columns} are not in any group. Update config file."
        )

    return feature_group_lists


def load_config_file(config_file):
    with open(config_file, "r") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as e:
            raise RuntimeError(f"Unable to load config file: {e}")

class Dataset:
    def __init__(self, name, config_file, sparse_features, interactive=True):
        """
        Contains a dataset as a feature matrix X and outcome
        vector y, along with information about the dataset
        (such as what file it was loaded from, the feature
        names, feature groups, etc.)

        The file will be loaded from a folder called datasets/
        relative to the current working directory. Pass the
        name (the first part of the filename) to interactively
        pick which to load (displayed by timestamp and commit
        hash).

        Feature and outcome column names are loaded from
        config_file. This allows the dataset to be partitioned
        into X and y (which are converted to numpy arrays), and
        keeps track of which column indices correspond to which
        feature groups.
        """

        if interactive:
            self.dataset_path = pick_file_interactive(name)
        else:
            self.dataset_path = pick_most_recent_file(name)
        print(f"Loading {self.dataset_path}")
        dataset = pd.read_pickle(self.dataset_path)

        # Load the configuration file
        self.config = load_config_file(config_file)

        # Reduce the date range
        # dataset = dataset[(dataset.idx_date > '2018-1-1') & (dataset.idx_date < '2022-1-1')]
        # print(f"Dataset number of rows: {dataset.shape[0]}")

        # Drop columns that are in the ignore list
        dataset.drop(columns=self.config["ignore"], inplace=True)

        # Get the outcome columns
        outcome_columns = self.config["outcomes"].values()
        try:
            dataset_outcomes = dataset.loc[:, outcome_columns]
        except KeyError as e:
            raise ValueError(
                "Could not find outcome column specified "
                + f"in '{config_file}' in dataset: {e}"
            )

        # Convert the outcome columns to a matrix and store the indices.
        # (use get_y() to get an outcome column)
        self._outcome_to_index = {
            col: dataset_outcomes.columns.get_loc(col) for col in outcome_columns
        }
        self._Y = dataset_outcomes.to_numpy()

        # Get the feature matrix
        dataset_features = dataset.drop(columns=outcome_columns)
        self.feature_names = dataset_features.columns

        # Before converting the columns to numpy arrays, record the
        # types of each column for preprocessing purposes
        dtypes = dataset_features.dtypes
        object_columns = dtypes[dtypes == np.dtype("O")].index
        self.object_column_indices = [
            dataset_features.columns.get_loc(col) for col in object_columns
        ]

        print(dataset_features.info())
        if sparse_features:
            # Attempt to convert all object columns to numeric
            dataset_features[object_columns] = dataset_features[object_columns].apply(pd.to_numeric, errors='coerce')
            self._X = csr_matrix(dataset_features.to_numpy())
            self.object_column_indices = []
        else:
            self._X = dataset_features.to_numpy()

        # Store the map from feature name to column index in _X
        self._feature_to_index = {
            col: dataset_features.columns.get_loc(col) for col in self.feature_names
        }

        # Store the map from group names to lists of feature columns
        self._feature_groups = match_feature_list(
            self.feature_names, self.config["features"]
        )

    def __str__(self):
        return f"Dataset {self.dataset_path} ({self._X.shape[0]} rows) with feature groups {self.feature_groups()} and outcomes {self.outcome_columns()}"

    def get_X(self):
        """Get the numpy matrix of features"""
        return self._X

    def get_y(self, outcome_name):
        """Get a particular outcome vector y

        Args:
            outcome_name (str): the name of the outcome vector.
            if the outcome_name is not an outcome column name,
            ValueError is raised

        """
        if outcome_name not in self._outcome_to_index:
            raise ValueError(f"Outcome column '{outcome_name}' not present in dataset")
        else:
            return self._Y[:, self._outcome_to_index[outcome_name]]

    def outcome_columns(self):
        """Get the list of outcome column names for use with get_y()"""
        return list(self._outcome_to_index.keys())

    def feature_groups(self):
        """Get a map from feature groups to lists of columns in that
        group"""
        result = {}
        for group, feature_column_list in self._feature_groups.items():
            result[group] = [
                self.feature_names.get_loc(col) for col in feature_column_list
            ]
        return result
