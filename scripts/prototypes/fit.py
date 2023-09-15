# Model fitting function
#
# This file contains the process referred to in
# stability.py as D, which takes as input a training
# set (X, y), and outputs a scikit-learn pipeline.
#
# The feature matrix X is a numerical array where
# columns are predictors (features) and rows are
# samples corresponding to an outcome in the vector
# y. As far as possible, X should be preprocessed
# before handing it over to this function. However,
# this preprocessing must _not_ include any information
# from the testing set. More generally, we only allow
# preprocessing that applies an operation to each
# sample of the dataset that is:
#
# - local, meaning it only involves values from the
#   given row of X.
# - determinstic, meaning it does not involve any
#   elements of randomness.
# - non-parametrised, meaning the preprocessing does
#   not depend on parameters which may need to be
#   tuned over.
#
# These conditions are stronger than required to
# prevent leakage of test data into training data,
# but are designed to push non-trivial preprocessing
# into the model development pipeline where it can
# be tuned and consistently applied to training and
# testing data.
#
# Examples of preprocessing that can be performed on
# X before passing it to the fit functions:
#
# - Creating a feature by counting the number of
#   diagnosis codes before the index event. This
#   is a local (to the index event) operation
#   which is non-parametric and deterministic.
# - Creating features which are deterministic
#   functions of the index event (for example, whether
#   the index MI is STEMI or NSTEMI).
#
# Examples of preprocessing that must not be performed
# on X before passing it to the fit functions

#
# - Any imputing of data which involves a global
#   computation (such as imputing an age column based
#   on the mean)
# - Any dimension reduction (such as UMAP) that depends
#   on tuning parameters and is also a global operation.
# - Any centering and scaling, which is a global operation.
#

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import pandas as pd
from sklearn import tree
from transformers import RemoveMajorityZero


class SimpleDecisionTree:
    def __init__(self, X, y):
        """
        Simple decision tree model with no feature preprocessing.
        """
        tree = DecisionTreeClassifier(max_depth=3)
        self.pipe = Pipeline([("tree", tree)])
        self.pipe.fit(X, y)

    def plot(self):
        plot_tree(self.pipe["tree"])


class SimpleLogisticRegression:
    def __init__(self, X, y):
        """
        Logistic regress class that centers and scales the features
        and applies logistic regression to the result. The pipe 
        comprises a StandardScaler() followed by LogisticRegression().
        There is no hyperparameter tuning or cross-validation.

        Testing: not yet tested
        """

        # majority_zero = RemoveMajorityZero(0.1)
        scaler = StandardScaler()
        logreg = LogisticRegression()
        self.pipe = Pipeline([("scaler", scaler), ("logreg", logreg)])
        self.pipe.fit(X, y)

    def get_model_parameters(self, feature_names):
        """
        Get the fitted model parameters as a dataframe with one
        row per feature. Two columns for the scaler contain the
        mean and variance, and the final column contains the
        logistic regression coefficient. You must pass the vector
        of feature names in the same order as columns of X in the
        constructor.
        """
        means = self.pipe["scaler"].mean_
        variances = self.pipe["scaler"].var_
        coefs = self.pipe["logreg"].coef_[0, :]
        model_params = pd.DataFrame(
            {
                "feature": feature_names,
                "scaling_mean": means,
                "scaling_variance": variances,
                "logreg_coef": coefs,
            }
        )
        return model_params



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
