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

    #fig, ax = plt.subplots(2,2, figsize=(8,5), layout="constrained")

    # Plot the basic instability curve
    fig, ax = plt.subplots()
    plot_instability(ax, d["probs"], d["y_test"])
    plt.show()
    
    fig, ax = plt.subplots()
    plot_prediction_distribution(ax, d["probs"], n_bins=50)
    plt.show()

    # Plot the ROC-stability curves
    fig, ax = plt.subplots()
    plot_roc_curves(ax, roc_curves, roc_auc)
    plt.show()

    # Plot the calibration-stability plots
    fig, ax = plt.subplots(2,1)
    plot_calibration_curves(ax[0], calibration_curves)
    # Plot the distribution of predicted probabilities, also
    # showing distribution stability (over the bootstrapped models)
    # as error bars on each bin height
    plot_prediction_distribution(ax[1], d["probs"], n_bins=10)
    plt.show()

def plot_risk_tradeoff(model_name, bleeding_outcome, ischaemia_outcome):
    
    filename_bleeding = model_name + "_" + bleeding_outcome
    d_bleeding = ds.load_fit_info(filename_bleeding)

    filename_ischaemia = model_name + "_" + ischaemia_outcome
    d_ischaemia = ds.load_fit_info(filename_ischaemia)
    
    # Get just the main model predictions
    probs_bleeding = d_bleeding["probs"][:,0]
    y_test_bleeding = d_bleeding["y_test"]
    
    probs_ischaemia = d_ischaemia["probs"][:,0]
    y_test_ischaemia = d_ischaemia["y_test"]
    
    fig, ax = plt.subplots()
    
    num_rows = len(probs_bleeding)
    x = []
    y = []
    c = [] # 0 = nothing, 1 = bleeding, 2 = ischaemia, 3 = bleeding and ischaemia
    for i in range(num_rows):
        x.append(probs_bleeding[i])
        y.append(probs_ischaemia[i])
        # Create number by concatenating bleeding and ischaemia bits (binary)
        c.append(y_test_ischaemia[i] + 2*y_test_bleeding[i])
    
    colour_map = {0: "g", 1: "b", 2: "r", 3: "m"}

    for outcome_to_plot, colour in colour_map.items():
       x_to_plot = [x for x, outcome in zip(x, c) if outcome == outcome_to_plot]
       y_to_plot = [y for y, outcome in zip(y, c) if outcome == outcome_to_plot]
       ax.scatter(x_to_plot, y_to_plot, c=colour, s=1, marker=".")
    
    ax.set_title("Bleeding/ischaemia risk trade-off")
        
    ax.legend(
    [   
        "Nothing (background)",
        "Ischaemia",
        "Bleeding",
        "Bleeding and ischaemia (foreground)",
    ],
    markerscale=15
)
    
    ax.set_xscale("log")
    ax.set_xlabel("Bleeding risk")
    
    ax.set_yscale("log")
    ax.set_ylabel("Ischaemia risk")
    plt.show()
    

# If you run this script as python ./plot_model.py, then
# plot a particular model
if __name__ == "__main__":
    #plot_model_validation_2page("truncsvd_logistic_regression", "bleeding_al_ani_outcome")
    plot_risk_tradeoff("truncsvd_logistic_regression", "bleeding_al_ani_outcome", "hussain_ami_stroke_outcome")
    