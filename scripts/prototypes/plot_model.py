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

#plt.rcParams.update({"legend.fontsize": 4})

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

    fig, ax = plt.subplots(2,2, figsize=(8,5), layout="constrained")

    # Plot the basic instability curve
    plot_instability(ax[0][0], d["probs"], d["y_test"])

    # Plot the ROC-stability curves
    plot_roc_curves(ax[0][1], roc_curves, roc_auc)

    # Plot the calibration-stability plots
    plot_calibration_curves(ax[1][0], calibration_curves)
    # Plot the distribution of predicted probabilities, also
    # showing distribution stability (over the bootstrapped models)
    # as error bars on each bin height
    plot_prediction_distribution(ax[1][1], d["probs"], n_bins=10)
    
    plt.show()
