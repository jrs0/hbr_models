# Plot model saved in the datasets/ folder

from calibration import (
    get_bootstrapped_calibration,
    get_average_calibration_error,
    plot_calibration_curves,
    plot_prediction_distribution,
)
import save_datasets as ds
from roc import get_bootstrapped_roc, get_bootstrapped_auc, plot_roc_curves
from stability import (
    plot_instability,
    get_average_instability
)
import matplotlib.pyplot as plt
import pandas as pd

from IPython.display import display, Markdown

def get_nonzero_proportion(df):
    """
    Utility function to (interactively) show the proportion
    of each feature that is non-zero. Pass a pandas dataframe
    df. A low result means that a column is mostly zero. Used
    to decide it it might be helpful to remove features based
    on high proportion of zeros.

    Testing: not yet tested
    """
    return df.astype(bool).mean()

def get_model_summary(dataset, model, outcome):
    """
    Get a summary of the model as a pandas table with a single
    row. Contains ROC AUC, estimated calibration error (ECE),
    and average relative instability
    """
    filename = f"{dataset}_{model}_{outcome}"
    d = ds.load_fit_info(filename)
    
    # The first item in the array is the model-under-test AUC
    roc_auc = get_bootstrapped_auc(d["probs"], d["y_test"])[0]
    ece = get_average_calibration_error(d["probs"], d["y_test"], n_bins=10)
    instability = get_average_instability(d["probs"])
    
    data = {
        "ROC AUC": [roc_auc],
        "Cal. Error": [ece],
        "Instability": [instability],
    }
    return pd.DataFrame(data)

def plot_roc_and_calibration_2x2(dataset, model, bleeding_outcome, ischaemia_outcome):
    
    filename = f"{dataset}_{model}_{bleeding_outcome}"
    d_bleeding = ds.load_fit_info(filename)

    filename = f"{dataset}_{model}_{ischaemia_outcome}"
    d_ischaemia = ds.load_fit_info(filename)

    # Get the bootstrapped ROC curves
    roc_curves_bleeding = get_bootstrapped_roc(d_bleeding["probs"], d_bleeding["y_test"])
    roc_auc_bleeding = get_bootstrapped_auc(d_bleeding["probs"], d_bleeding["y_test"])
    roc_curves_ischaemia = get_bootstrapped_roc(d_ischaemia["probs"], d_ischaemia["y_test"])
    roc_auc_ischaemia = get_bootstrapped_auc(d_ischaemia["probs"], d_ischaemia["y_test"])
    
    # Get the bootstrapped calibration curves
    calibration_curves_bleeding = get_bootstrapped_calibration(d_bleeding["probs"], d_bleeding["y_test"], n_bins=10)
    calibration_curves_ischaemia = get_bootstrapped_calibration(d_ischaemia["probs"], d_ischaemia["y_test"], n_bins=10)
    
    fig, ax = plt.subplots(2,2, figsize=(8,7))
    
    # Plot the ROC-stability curves
    plot_roc_curves(ax[0][0], roc_curves_bleeding, roc_auc_bleeding, title="Bleeding ROC Curves")
    plot_roc_curves(ax[0][1], roc_curves_ischaemia, roc_auc_ischaemia, title="Ischaemia ROC Curves")
    
    # Plot the calibration-stability plots
    plot_calibration_curves(ax[1][0], calibration_curves_bleeding, title="Bleeding Calibration Curves")
    plot_calibration_curves(ax[1][1], calibration_curves_ischaemia, title="Ischaemia Calibration Curves")
    
    fig.tight_layout()
    
    plt.show()
    
def plot_instability_2x2(dataset, model, bleeding_outcome, ischaemia_outcome):
    
    filename = f"{dataset}_{model}_{bleeding_outcome}"
    d_bleeding = ds.load_fit_info(filename)

    filename = f"{dataset}_{model}_{ischaemia_outcome}"
    d_ischaemia = ds.load_fit_info(filename)
    
    fig, ax = plt.subplots(2,2, figsize=(8,7))
    
    # Plot the stability curves
    plot_instability(ax[0][0], d_bleeding["probs"], d_bleeding["y_test"], title="Bleeding Prediction Stability")
    plot_instability(ax[0][1], d_ischaemia["probs"], d_ischaemia["y_test"], title = "Ischaemia Prediction Stability")
    plot_prediction_distribution(ax[1][0], d_bleeding["probs"], n_bins=50) 
    plot_prediction_distribution(ax[1][1], d_ischaemia["probs"], n_bins=50) 
    
    fig.tight_layout()
    plt.show()

def plot_model_validation_2page(dataset, model, outcome):
    """
    Plot the four model-validation plots -- probability
    stability and ROC curve, and the calibration plots.
    If called from inside quarto, this will take up two
    PDF pages. If called interactively, the plots will be
    generated one by one.
    """
    filename = f"{dataset}_{model}_{outcome}"
    d = ds.load_fit_info(filename)

    # Get the bootstrapped ROC curves
    roc_curves = get_bootstrapped_roc(d["probs"], d["y_test"])
    roc_auc = get_bootstrapped_auc(d["probs"], d["y_test"])

    # Get the bootstrapped calibration curves
    calibration_curves = get_bootstrapped_calibration(d["probs"], d["y_test"], n_bins=10)

    fig, ax = plt.subplots(2,1, figsize=(6,8))
    
    # Plot the basic instability curve for probabilities, along with the
    # probability distribution
    plot_instability(ax[0], d["probs"], d["y_test"])
    plot_prediction_distribution(ax[1], d["probs"], n_bins=50) 
    plt.show()

    # Output a page break
    display(Markdown("\n"))

    # Plot the ROC-stability curves
    fig, ax = plt.subplots(2,1, figsize=(6,8))
    plot_roc_curves(ax[0], roc_curves, roc_auc)
    # Plot the calibration-stability plots
    plot_calibration_curves(ax[1], calibration_curves)
    # Plot the distribution of predicted probabilities, also
    # showing distribution stability (over the bootstrapped models)
    # as error bars on each bin height
    #plot_prediction_distribution(ax[1], d["probs"], n_bins=10)
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
    dataset = "manual_codes_swd"
    model = "simple_decision_tree"
    df1 = get_model_summary(dataset, model, "bleeding_al_ani_outcome")
    df2 = get_model_summary(dataset, model, "hussain_ami_stroke_outcome")
    df = pd.concat([df1, df2]).reset_index(drop=True)
    print(df)
    print(df["Instability"].idxmin())
    

    plot_roc_and_calibration_2x2(dataset, model, "bleeding_al_ani_outcome", "hussain_ami_stroke_outcome")
    #plot_risk_tradeoff("simple_logistic_regression", "bleeding_al_ani_outcome", "hussain_ami_stroke_outcome")
    