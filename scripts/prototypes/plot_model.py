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

d = ds.load_fit_info("simple_logistic_regression")
print(f"Model name: {d['model_name']}")
print(f"Dataset path: {d['dataset_path']}")

# Plot the basic instability curve
fig, ax = plt.subplots()
plot_instability(ax, d["probs"], d["y_test"])
plt.show()

# Get the bootstrapped calibration curves
calibration_curves = get_bootstrapped_calibration(d["probs"], d["y_test"], n_bins=10)

# Plot the calibration-stability plots
fig, ax = plt.subplots(2, 1)
plot_calibration_curves(ax[0], calibration_curves)
# Plot the distribution of predicted probabilities, also
# showing distribution stability (over the bootstrapped models)
# as error bars on each bin height
plot_prediction_distribution(ax[1], d["probs"], n_bins=10)
plt.show()

# Get the bootstrapped ROC curves
roc_curves = get_bootstrapped_roc(d["probs"], d["y_test"])
roc_auc = get_bootstrapped_auc(d["probs"], d["y_test"])

# Plot the ROC-stability curves
fig, ax = plt.subplots()
plot_roc_curves(ax, roc_curves, roc_auc)
plt.show()
