# Plot model saved in the datasets/ folder

from calibration import (
    get_bootstrapped_calibration,
    plot_calibration_curves,
    plot_prediction_distribution,
)
import save_datasets as ds
from roc import get_bootstrapped_roc, get_bootstrapped_auc, plot_roc_curves
from stability import (
    plot_instability,
)
import matplotlib.pyplot as plt

def plot_model_validation_2page(model_name, outcome):
    """
    Plot the four model-validation plots -- probability
    stability and ROC curve, and the calibration plots.
    If called from inside quarto, this will take up two
    PDF pages. If called interactively, the plots will be
    generated one by one.
    
    Pass in the model name and outcome name./
    """
    filename = model_name + "_" + outcome
    d = ds.load_fit_info(filename)

    # Get the bootstrapped ROC curves
    roc_curves = get_bootstrapped_roc(d["probs"], d["y_test"])
    roc_auc = get_bootstrapped_auc(d["probs"], d["y_test"])

    # Get the bootstrapped calibration curves
    calibration_curves = get_bootstrapped_calibration(d["probs"], d["y_test"], n_bins=10)

    # Plot the basic instability curve
    fig, ax = plt.subplots(figsize=(6,4))
    plot_instability(ax, d["probs"], d["y_test"])
    plt.show()

    # Plot the ROC-stability curves
    fig, ax = plt.subplots(figsize=(6,4))
    plot_roc_curves(ax, roc_curves, roc_auc)
    plt.show()

    # Plot the calibration-stability plots
    fig, ax = plt.subplots(2, 1, figsize=(6,8))
    plot_calibration_curves(ax[0], calibration_curves)
    # Plot the distribution of predicted probabilities, also
    # showing distribution stability (over the bootstrapped models)
    # as error bars on each bin height
    plot_prediction_distribution(ax[1], d["probs"], n_bins=10)
    plt.show()
