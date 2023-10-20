import save_datasets as ds
import numpy as np
from sklearn.model_selection import train_test_split
from stability import fit_model, predict_bootstrapped_proba


def fit_and_save(model_data):
    """
    Load and split a dataset into testing and training.
    Fit the model on the training, and also fit the model on
    resamples of the training for checking stability. Save the
    resulting model to a file, with enough data to plot results.
    """
    dataset = ds.Dataset(
        model_data["dataset_name"],
        model_data["config_file"],
        model_data["sparse_features"],
    )

    # Store the indices of columns which need to be dummy encoded.
    # This is passed to the models, which do the encoding as a 
    # preprocessing step.
    object_column_indices = dataset.object_column_indices

    # Get the feature matrix X and outcome vector y
    X = dataset.get_X()

    # outcome = hussain_ami_stroke_outcome
    y = dataset.get_y(model_data["outcome"])


    # Split (X,y) into a testing set (X_test, y_test), which is not used for
    # any model training, and a training set (X0,y0), which is used to develop
    # the model. Later, (X0,y0) is resampled to generate M additional training
    # sets (Xm,ym) which are used to assess the stability of the developed model
    # (see stability.py). All models are tested using the testing set.
    train_test_split_rng = np.random.RandomState(0)
    test_set_proportion = 0.25
    X0_train, X_test, y0_train, y_test = train_test_split(
        X, y, test_size=test_set_proportion, random_state=train_test_split_rng
    )

    print(f"Training dataset contains {X0_train.shape[0]} rows")
    print(f"Outcome vector has mean {np.mean(y0_train)}")

    Model = model_data["model"]

    # Fit the model-under-test M0 to the training set (X0_train, y0_train), and
    # fit M other models to M other bootstrap resamples of (X0_train, y0_train).
    M0, Mm = fit_model(Model, object_column_indices, X0_train, y0_train, M=10)

    # First columns is the probability of 1 in y_test from M0; other columns
    # are the same for the N bootstrapped models Mm.
    probs = predict_bootstrapped_proba(M0, Mm, X_test)

    # At this point, all you need to save is probs, y_test, and any information
    # about the best model fit that you want (i.e. params, preprocessing steps, etc.)
    fit_data = {
        "model_name": Model.name(),
        "dataset_path": dataset.dataset_path,
        "model": M0,
        "probs": probs,
        "y_test": y_test,
    } | model_data

    filename = f"{fit_data['dataset_name']}_{fit_data['model_name']}_{fit_data['outcome']}"
    ds.save_fit_info(fit_data, filename)
