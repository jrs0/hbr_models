# Calibration plots
#
# A calibration plot is a comparison of the proportion p
# of events that occur in the subset of those with predicted
# probability p'. Ideally, p = p' meaning that of the
# cases predicted to occur with probability p', p of them
# do occur. Calibration is presented as a plot of p against
# p'.
#
# The stability of the calibration can be investigated, by
# plotting p against p' for multiple bootstrapped models
# (see stability.py).

import numpy as np
from sklearn.calibration import calibration_curve


def get_bootstrapped_calibration(probs, y_test, n_bins):
    """
    Get the calibration curves for all models (whose probability
    predictions for the positive class are columns of probs) based
    on the outcomes in y_test. Rows of y_test correspond to rows of
    probs. The result is a list of pairs, one for each model (column
    of probs). Each pair contains the vector of x- and y-coordinates
    of the calibration curve.

    Testing: not yet tested
    """
    curves = []
    for n in range(probs.shape[1]):
        # Reverse because it is more convenient to have the x-axis first
        curves.append(
            tuple(reversed(calibration_curve(y_test, probs[:, n], n_bins=n_bins)))
        )
    return curves


def plot_calibration_curves(ax, curves):
    """
    Plot the set of bootstrapped calibration curves (an instability plot),
    using the data in curves (a list of curves to plot). Assume that the
    first curve is the model-under-test (which is coloured differently).
    """
    ax.axline([0, 0], [1, 1], color="k", linestyle="--")

    mut_curve = curves[0]  # model-under-test
    ax.plot(
        mut_curve[0],
        mut_curve[1]
    )
    for curve in curves[1:]:
        ax.plot(curve[0], curve[1], color="b", linewidth=0.3, alpha=0.2)
    ax.legend(["Ideal calibration", "Model-under-test", "Bootstrapped models"])
    ax.set_title("Calibration-stability curves")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives")


def plot_prediction_distribution(ax, probs, n_bins):
    """
    Plot the distribution of predicted probabilities over the models as
    a bar chart, with error bars showing the standard deviation of each
    model height. All model predictions (columns of probs) are given equal
    weight in the average; column 0 (the model under test) is not singled
    out in any way.

    The function plots vertical error bars that are one standard deviation
    up and down (so 2*sd in total)
    """
    bin_edges = np.linspace(0, 1, n_bins + 1)
    freqs = []
    for j in range(probs.shape[1]):
        f, _ = np.histogram(probs[:, j], bins=bin_edges)
        freqs.append(f)
    means = np.mean(freqs, axis=0)
    sds = np.std(freqs, axis=0)

    bin_centers = (bin_edges[1:] + bin_edges[:-1]) / 2

    ax.bar(bin_centers, height=means, width=0.05, yerr=2 * sds)
    #ax.set_title("Distribution of predicted probabilities")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Count")