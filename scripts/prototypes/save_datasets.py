import time, git
import os
import pandas as pd


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


def load_dataset(name):
    # Check for missing datasets directory
    datasets_dir = "datasets"

    if not os.path.isdir(datasets_dir):
        raise RuntimeError(
            f"Missing folder '{datasets_dir}'. Check your working directory."
        )

    # Read all the .pkl files in the directory
    files = pd.DataFrame({"path": os.listdir(datasets_dir)})

    # Remove all the files whose name does not match, and drop
    # the name from the path
    files = files[files["path"].str.contains(name)]
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
    recent_first = files.sort_values(by="timestamp", ascending=False)
    full_path = os.path.join(datasets_dir, recent_first.reset_index().loc[0, "path"])
    dataset = pd.read_pickle(full_path)
    return dataset


load_dataset("hes_episodes_dataset")
