# ROC Curves
#
# The file calculates the ROC curves of the bootstrapped
# models (for assessing ROC curve stability; see stability.py).
#

import numpy as np
from sklearn.metrics import roc_curve, roc_auc_score


def get_bootstrapped_roc(probs, y_test):
    """
    Get the ROC curves for all models (whose probability
    predictions for the positive class are columns of probs) based
    on the outcomes in y_test. Rows of y_test correspond to rows of
    probs. The result is a list of pairs, one for each model (column
    of probs). Each pair contains the vector of x- and y-coordinates
    of the ROC curve.

    Testing: not yet tested
    """
    curves = []
    for n in range(probs.shape[1]):
        fpr, tpr, _ = roc_curve(y_test, probs[:, n])
        curves.append((fpr, tpr))
    return curves

def get_bootstrapped_auc(probs, y_test):
    """
    Compute area under the ROC curve (AUC) for the model-under-test
    (the first column of probs), and the other bootstrapped models
    (other columns of probs). The result is an array with the
    following three elements (in order):
    - model-under-test AUC
    - mean of the AUC of bootstrapped models
    - standard deviation of AUC of bootstrapped models
    
    Testing: not yet tested
    """
    mut_auc = roc_auc_score(y_test, probs[:,0]) # Model-under test
    bootstrapped_auc = [roc_auc_score(y_test, col) for col in probs.T]
    mean_bootstrapped_auc = np.mean(bootstrapped_auc)
    sd_bootstrapped_auc = np.std(bootstrapped_auc)
    return [mut_auc, mean_bootstrapped_auc, sd_bootstrapped_auc]

def plot_roc_curves(ax, curves, auc):
    """
    Plot the set of bootstrapped ROC curves (an instability plot),
    using the data in curves (a list of curves to plot). Assume that the
    first curve is the model-under-test (which is coloured differently).

    The auc argument is an array where the first element is the AUC of the
    model under test, and the second element is the mean AUC of the
    bootstrapped models, and the third element is the standard deviation
    of the AUC of the bootstrapped models (these latter two measure
    stability). This argument is the output from get_bootstrapped_auc.

    Testing: not yet tested
    """
    ax.axline([0, 0], [1, 1], color="k", linestyle="--")

    mut_curve = curves[0]  # model-under-test
    ax.plot(mut_curve[0], mut_curve[1], color="r")
    for curve in curves[1:]:
        ax.plot(curve[0], curve[1], color="b", linewidth=0.3, alpha=0.1)
    ax.legend(
        [
            "Chance level (AUC = 0.5)",
            f"Model-under-test (AUC = {auc[0]:.2f})",
            f"Bootstrapped models (AUC = {auc[1]:.2f} $\pm$ {auc[2]:.2f})",
        ]
    )
    ax.set_title("ROC-stability curves")
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
