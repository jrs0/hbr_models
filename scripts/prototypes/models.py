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
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer

from imblearn.over_sampling import RandomOverSampler

# from sklearn.pipeline import Pipeline
from imblearn.pipeline import Pipeline
import pandas as pd
from sklearn import tree
from transformers import RemoveMajorityZero
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
import umap
from sklearn.decomposition import TruncatedSVD
from scipy.stats import uniform


# This should go inside each class, but for now it is just a dictionary to
# record the descriptions of each model in a way that can be incorporated in
# the report
model_description = {}

def get_model_description(model_name):
    try:
        return model_description[model_name]
    except:
        return "No description yet"

class SimpleLogisticRegression:
    def __init__(self, X, y, object_column_indices):
        """
        Fit basic logistic regression with not hyperparameter
        tuning or cross-validation (because basic logistic regression
        has no tuning parameters). Expects X to be preprocessed by
        the preprocess argument into a matrix of features ready for
        logistic regression.

        preprocess is a list of pairs mapping preprocessing step
        names to preprocessing steps, in the format suitable for
        use in Pipeline.

        Testing: not yet tested
        """

        # Many columns, particular in the SWD, contain string values that
        # correspond to a discrete set of categories. These are encoded using
        # one-hot encoding (one column per value). The logistic regression
        # includes ridge penalisation by default, so there is no issue with
        # colinearity.
        to_numeric = ColumnTransformer(
            [
                (
                    "one_hot",
                    OneHotEncoder(
                        sparse_output=False, handle_unknown="infrequent_if_exist"
                    ),
                    object_column_indices,
                )
            ],
            remainder="passthrough",
        )
        scaler = StandardScaler()
        # Many columns, particularly in the SWD, contain missing values. after
        # conversion to numeric. These are imputed because the scikit-learn
        # logistic regression implementation does not handle NaN by default.
        # Note that these missing values are not the ones in primary_care_attributes
        # corresponding to 0, which have already be recoded as 0.
        impute = SimpleImputer()
        logreg = LogisticRegression(verbose=0)
        self._pipe = Pipeline(
            [
                ("to_numeric", to_numeric),
                ("scaler", scaler),
                ("impute", impute),
                ("logreg", logreg),
            ]
        )
        self._pipe.fit(X, y)

    def name():
        return "simple_logistic_regression"

    def model(self):
        """
        Get the fitted logistic regression model
        """
        return self._pipe


model_description[SimpleLogisticRegression.name()] = (
    "The model is fitted by one-hot encoding catagorical features, "
    "centering and scaling predictors, and imputing missing values "
    "using the training set mean. No hyperparameters are tuned when "
    "fitting logistic regression. "
)


class TruncSvdLogisticRegression:
    def __init__(self, X, y, object_column_indices):
        to_numeric = ColumnTransformer(
            [
                (
                    "one_hot",
                    OneHotEncoder(
                        sparse_output=False, handle_unknown="infrequent_if_exist"
                    ),
                    object_column_indices,
                )
            ],
            remainder="passthrough",
        )
        impute = SimpleImputer()
        reducer = TruncatedSVD(n_iter=7)
        scaler = StandardScaler()
        logreg = LogisticRegression()
        # If there are no object columns, then omit the step
        # which converts to numeric
        if len(object_column_indices) == 0:
            self._pipe = Pipeline(
                [
                    ("impute", impute),
                    ("reducer", reducer),
                    ("scaler", scaler),
                    ("logreg", logreg),
                ]
            )
        else:
            self._pipe = Pipeline(
                [
                    ("to_numeric", to_numeric),
                    ("impute", impute),
                    ("reducer", reducer),
                    ("scaler", scaler),
                    ("logreg", logreg),
                ]
            )
        num_features = X.shape[1]
        max_components = min(num_features, 200)

        self._param_grid = {
            "reducer__n_components": range(1, max_components),
        }
        self._search = RandomizedSearchCV(
            self._pipe,
            self._param_grid,
            cv=5,
            verbose=3,
            scoring="roc_auc",
            error_score="raise",
        ).fit(X, y)
        print(self._search.best_params_)

        self._pipe.fit(X, y)

    def name():
        return "truncsvd_logistic_regression"

    def model(self):
        """
        Get the fitted logistic regression model
        """
        return self._search.best_estimator_

model_description[TruncSvdLogisticRegression.name()] = (
    "The model is fitted by one-hot encoding catagorical features, "
    "centering and scaling predictors, and imputing missing values "
    "using the training set mean. Dimensionality reduction using truncated "
    "singular value decomposition is performed, using the resulting number of "
    "features as a hyperparameter, before fitting logistic regression."
)

class SimpleDecisionTree:
    def __init__(self, X, y, object_column_indices):
        """
        Simple decision tree model with no feature preprocessing.
        """
        to_numeric = ColumnTransformer(
            [
                (
                    "one_hot",
                    OneHotEncoder(
                        sparse_output=False, handle_unknown="infrequent_if_exist"
                    ),
                    object_column_indices,
                )
            ],
            remainder="passthrough",
        )
        impute = SimpleImputer()
        tree = DecisionTreeClassifier()
        if len(object_column_indices) == 0:
            self._pipe = Pipeline(
                [("to_numeric", to_numeric), ("impute", impute), ("tree", tree)]
            )
        else:
            self._pipe = Pipeline([("impute", impute), ("tree", tree)])

        self._param_grid = {"tree__max_depth": range(1, 15)}
        self._search = GridSearchCV(
            self._pipe, self._param_grid, cv=5, verbose=3, scoring="roc_auc"
        ).fit(X, y)
        print(self._search.best_params_)

    def name():
        return "simple_decision_tree"

    def model(self):
        """
        Get the best fitted model from the hyperparameter search results
        """
        return self._search.best_estimator_

    def plot(self, ax, feature_names):
        plot_tree(
            self.model()["tree"],
            feature_names=feature_names,
            class_names=["bleed", "no_bleed"],
            filled=True,
            rounded=True,
            fontsize=10,
            ax=ax,
        )

model_description[SimpleDecisionTree.name()] = (
    "The model is fitted by one-hot encoding catagorical features, "
    "centering and scaling predictors, and imputing missing values "
    "using the training set mean. A decision tree is fitted using "
    "the maximum tree depth as a tuned hyperparameter."
)

class TruncSvdDecisionTree:
    def __init__(self, X, y, object_column_indices):
        to_numeric = ColumnTransformer(
            [
                (
                    "one_hot",
                    OneHotEncoder(
                        sparse_output=False, handle_unknown="infrequent_if_exist"
                    ),
                    object_column_indices,
                )
            ],
            remainder="passthrough",
        )
        impute = SimpleImputer()
        reducer = TruncatedSVD(n_iter=7)
        scaler = StandardScaler()
        tree = DecisionTreeClassifier()
        if len(object_column_indices) == 0:
            self._pipe = Pipeline(
                [
                    ("impute", impute),
                    ("reducer", reducer),
                    ("scaler", scaler),
                    ("tree", tree),
                ]
            )
        else:
            self._pipe = Pipeline(
                [
                    ("to_numeric", to_numeric),
                    ("impute", impute),
                    ("reducer", reducer),
                    ("scaler", scaler),
                    ("tree", tree),
                ]
            )

        num_features = X.shape[1]
        max_components = min(num_features, 200)
        self._param_grid = {
            "reducer__n_components": range(1, max_components),
            "tree__max_depth": range(1, 20),
        }
        self._search = RandomizedSearchCV(
            self._pipe, self._param_grid, cv=5, verbose=3, scoring="roc_auc"
        ).fit(X, y)
        print(self._search.best_params_)

        self._pipe.fit(X, y)

    def model(self):
        return self._search.best_estimator_

    def name():
        return "truncsvd_decision_tree"


model_description[TruncSvdDecisionTree.name()] = (
    "The model is fitted by one-hot encoding catagorical features, "
    "centering and scaling predictors, and imputing missing values "
    "using the training set mean. Dimensionality reduction using truncated "
    "singular value decomposition is performed, before fitting a decision "
    "tree. The number of output features of the dimensionality reduction and "
    "the maximum tree depth are tuned hyperparameters."
)

class SimpleRandomForest:
    def __init__(self, X, y, object_column_indices):
        to_numeric = ColumnTransformer(
            [
                (
                    "one_hot",
                    OneHotEncoder(
                        sparse_output=False, handle_unknown="infrequent_if_exist"
                    ),
                    object_column_indices,
                )
            ],
            remainder="passthrough",
        )
        impute = SimpleImputer()
        tree = RandomForestClassifier()
        if len(object_column_indices) == 0:
            self._pipe = Pipeline(
                [
                    ("impute", impute),
                    ("tree", tree),
                ]
            )
        else:
            self._pipe = Pipeline(
                [
                    ("to_numeric", to_numeric),
                    ("impute", impute),
                    ("tree", tree),
                ]
            )
        self._param_grid = {
            "tree__max_depth": range(1, 20),
        }
        self._search = RandomizedSearchCV(
            self._pipe, self._param_grid, cv=5, verbose=3, scoring="roc_auc"
        ).fit(X, y)
        print(self._search.best_params_)

        self._pipe.fit(X, y)

    def model(self):
        return self._search.best_estimator_

    def name():
        return "simple_random_forest"

model_description[SimpleRandomForest.name()] = (
    "The model is fitted by one-hot encoding catagorical features, "
    "centering and scaling predictors, and imputing missing values "
    "using the training set mean. A random forest is fitted using "
    "the maximum tree depth as a tuned hyperparameter."
)

# No predict_proba function
class SimpleLinearSvc:
    def __init__(self, X, y, object_column_indices):
        to_numeric = ColumnTransformer(
            [
                (
                    "one_hot",
                    OneHotEncoder(
                        sparse_output=False, handle_unknown="infrequent_if_exist"
                    ),
                    object_column_indices,
                )
            ],
            remainder="passthrough",
        )
        scaler = StandardScaler()
        impute = SimpleImputer()
        svc = LinearSVC(verbose=0)
        self._pipe = Pipeline(
            [
                ("to_numeric", to_numeric),
                ("scaler", scaler),
                ("impute", impute),
                ("svc", svc),
            ]
        )
        self._pipe.fit(X, y)

    def name():
        return "simple_linear_svc"

    def model(self):
        return self._pipe


class SimpleNaiveBayes:
    def __init__(self, X, y, object_column_indices):
        to_numeric = ColumnTransformer(
            [
                (
                    "one_hot",
                    OneHotEncoder(
                        sparse_output=False, handle_unknown="infrequent_if_exist"
                    ),
                    object_column_indices,
                )
            ],
            remainder="passthrough",
        )
        scaler = StandardScaler()
        impute = SimpleImputer()
        nb = GaussianNB()
        self._pipe = Pipeline(
            [
                ("to_numeric", to_numeric),
                ("scaler", scaler),
                ("impute", impute),
                ("nb", nb),
            ]
        )
        self._pipe.fit(X, y)

    def name():
        return "simple_naive_bayes"

    def model(self):
        return self._pipe

model_description[SimpleNaiveBayes.name()] = (
    "The model is fitted by one-hot encoding catagorical features, "
    "centering and scaling predictors, and imputing missing values "
    "using the training set mean. No hyperparameters are tuned when "
    "fitting naive bayes "
)

class SimpleGradientBoostedTree:
    def __init__(self, X, y, object_column_indices):
        to_numeric = ColumnTransformer(
            [
                (
                    "one_hot",
                    OneHotEncoder(
                        sparse_output=False, handle_unknown="infrequent_if_exist"
                    ),
                    object_column_indices,
                )
            ],
            remainder="passthrough",
        )
        impute = SimpleImputer()
        tree = GradientBoostingClassifier()
        if len(object_column_indices) == 0:
            self._pipe = Pipeline(
                [
                    ("impute", impute),
                    ("tree", tree),
                ]
            )
        else:
            self._pipe = Pipeline(
                [
                    ("to_numeric", to_numeric),
                    ("impute", impute),
                    ("tree", tree),
                ]
            )
        self._param_grid = {
            "tree__max_depth": range(1, 20),
        }
        self._search = RandomizedSearchCV(
            self._pipe, self._param_grid, cv=5, verbose=3, scoring="roc_auc"
        ).fit(X, y)
        print(self._search.best_params_)

        self._pipe.fit(X, y)

    def model(self):
        return self._search.best_estimator_

    def name():
        return "simple_gradient_boosted_tree"

model_description[SimpleGradientBoostedTree.name()] = (
    "The model is fitted by one-hot encoding catagorical features, "
    "centering and scaling predictors, and imputing missing values "
    "using the training set mean. A gradient boosted tree is fitted using "
    "the maximum tree depth as a tuned hyperparameter."
)

class SimpleNeuralNetwork:
    def __init__(self, X, y, object_column_indices):
        to_numeric = ColumnTransformer(
            [
                (
                    "one_hot",
                    OneHotEncoder(
                        sparse_output=False, handle_unknown="infrequent_if_exist"
                    ),
                    object_column_indices,
                )
            ],
            remainder="passthrough",
        )
        scaler = StandardScaler()
        impute = SimpleImputer()
        nn = MLPClassifier(
            solver="sgd",
            # alpha=1e-5,
            learning_rate="adaptive",
            verbose=False,
            max_iter=300,
        )
        if len(object_column_indices) == 0:
            self._pipe = Pipeline(
                [
                    ("impute", impute),
                    ("scaler", scaler),
                    ("nn", nn),
                ]
            )
        else:
            self._pipe = Pipeline(
                [
                    ("to_numeric", to_numeric),
                    ("impute", impute),
                    ("scaler", scaler),
                    ("nn", nn),
                ]
            )
        num_features = X.shape[1]
        max_neurons = min(num_features, 200)
        self._param_grid = {
            "nn__hidden_layer_sizes": range(5, max_neurons),
        }
        self._search = RandomizedSearchCV(
            self._pipe, self._param_grid, cv=5, verbose=3, scoring="roc_auc"
        ).fit(X, y)
        print(self._search.best_params_)

        self._pipe.fit(X, y)

    def model(self):
        return self._search.best_estimator_

    def name():
        return "simple_neural_network"

model_description[SimpleNeuralNetwork.name()] = (
    "The model is fitted by one-hot encoding catagorical features, "
    "centering and scaling predictors, and imputing missing values "
    "using the training set mean. A single-layer neural network is "
    "fitted with a number of internal neurons tuned as a hyperparameter."
)

####


class UmapLogisticRegression:
    def __init__(self, X, y):
        """
        Model which applies dimension reduction to the features before
        centering, scaling, and fitting logistic regression to the results.
        The pipe comprises a StandardScaler() followed by LogisticRegression().
        There is no hyperparameter tuning or cross-validation.

        Notes: Logistic regression after UMAP basically doesn't work (tried with
        n_components = 2, 5, 10, 25 and 50). I think the issue is that UAMP is
        coming out with random (very nonlinear) reductions, which something
        linear like logistic regression cannot deal with. A tree or a NN that
        can handle non-linearity may do better after UMAP. The model performance
        does improve a bit at n_components = 50, but the calibration is dreadful.

        Testing: not yet tested
        """

        # majority_zero = RemoveMajorityZero(0.1)
        reducer = umap.UMAP(metric="hamming", n_components=50, verbose=True)
        scaler = StandardScaler()
        logreg = LogisticRegression()
        self._pipe = Pipeline(
            [("reducer", reducer), ("scaler", scaler), ("logreg", logreg)]
        )
        self._pipe.fit(X, y)

    def model(self):
        """
        Get the fitted logistic regression model
        """
        return self._pipe

    def get_model_parameters(self, feature_names):
        """
        Get the fitted model parameters as a dataframe with one
        row per feature. Two columns for the scaler contain the
        mean and variance, and the final column contains the
        logistic regression coefficient. You must pass the vector
        of feature names in the same order as columns of X in the
        constructor.
        """
        means = self._pipe["scaler"].mean_
        variances = self._pipe["scaler"].var_
        coefs = self._pipe["logreg"].coef_[0, :]
        model_params = pd.DataFrame(
            {
                "feature": feature_names,
                "scaling_mean": means,
                "scaling_variance": variances,
                "logreg_coef": coefs,
            }
        )
        return model_params


class UmapMultiLayerPerceptron:
    def __init__(self, X, y):
        """
        Model which applies dimension reduction to the features before
        centering, scaling, and fitting a neural network to the results.
        The pipe comprises a StandardScaler() followed by MLPClassifier().
        There is no hyperparameter tuning or cross-validation.

        Notes:

        Testing: not yet tested
        """

        # majority_zero = RemoveMajorityZero(0.1)
        reducer = umap.UMAP(metric="hamming", n_components=50, verbose=True)
        scaler = StandardScaler()
        mlp = MLPClassifier(
            solver="lbfgs", alpha=1e-5, hidden_layer_sizes=(5, 2), verbose=True
        )
        self._pipe = Pipeline([("reducer", reducer), ("scaler", scaler), ("mlp", mlp)])
        self._pipe.fit(X, y)

    def model(self):
        """
        Get the fitted logistic regression model
        """
        return self._pipe

    def get_model_parameters(self, feature_names):
        """
        Get the fitted model parameters as a dataframe with one
        row per feature. Two columns for the scaler contain the
        mean and variance, and the final column contains the
        logistic regression coefficient. You must pass the vector
        of feature names in the same order as columns of X in the
        constructor.
        """
        means = self._pipe["scaler"].mean_
        variances = self._pipe["scaler"].var_
        coefs = self._pipe["logreg"].coef_[0, :]
        model_params = pd.DataFrame(
            {
                "feature": feature_names,
                "scaling_mean": means,
                "scaling_variance": variances,
                "logreg_coef": coefs,
            }
        )
        return model_params


class UmapDecisionTree:
    def __init__(self, X, y):
        """
        Model which applies dimension reduction to the features before
        centering, scaling, and fitting a neural network to the results.
        The pipe comprises a StandardScaler() followed by DecisionTreeCl().
        There is no hyperparameter tuning or cross-validation.

        Notes:

        Testing: not yet tested
        """

        # majority_zero = RemoveMajorityZero(0.1)
        reducer = umap.UMAP(metric="hamming", n_components=50, verbose=True)
        scaler = StandardScaler()
        tree = DecisionTreeClassifier(max_depth=8)
        self._pipe = Pipeline(
            [("reducer", reducer), ("scaler", scaler), ("tree", tree)]
        )
        self._pipe.fit(X, y)

    def model(self):
        """
        Get the fitted logistic regression model
        """
        return self._pipe

    def get_model_parameters(self, feature_names):
        """
        Get the fitted model parameters as a dataframe with one
        row per feature. Two columns for the scaler contain the
        mean and variance, and the final column contains the
        logistic regression coefficient. You must pass the vector
        of feature names in the same order as columns of X in the
        constructor.
        """
        means = self._pipe["scaler"].mean_
        variances = self._pipe["scaler"].var_
        coefs = self._pipe["logreg"].coef_[0, :]
        model_params = pd.DataFrame(
            {
                "feature": feature_names,
                "scaling_mean": means,
                "scaling_variance": variances,
                "logreg_coef": coefs,
            }
        )
        return model_params


class UmapGradientBoostedTree:
    def __init__(self, X, y):
        """
        Model which applies dimension reduction to the features before
        centering, scaling, and fitting a neural network to the results.
        The pipe comprises a StandardScaler() followed by DecisionTreeCl().
        There is no hyperparameter tuning or cross-validation.

        Notes:

        Testing: not yet tested
        """

        # majority_zero = RemoveMajorityZero(0.1)
        reducer = umap.UMAP(metric="hamming", n_components=50, verbose=True)
        scaler = StandardScaler()
        gbdt = DecisionTreeClassifier(max_depth=8)
        self._pipe = Pipeline(
            [("reducer", reducer), ("scaler", scaler), ("gbdt", gbdt)]
        )
        self._pipe.fit(X, y)

    def model(self):
        """
        Get the fitted logistic regression model
        """
        return self._pipe

    def get_model_parameters(self, feature_names):
        """
        Get the fitted model parameters as a dataframe with one
        row per feature. Two columns for the scaler contain the
        mean and variance, and the final column contains the
        logistic regression coefficient. You must pass the vector
        of feature names in the same order as columns of X in the
        constructor.
        """
        means = self._pipe["scaler"].mean_
        variances = self._pipe["scaler"].var_
        coefs = self._pipe["logreg"].coef_[0, :]
        model_params = pd.DataFrame(
            {
                "feature": feature_names,
                "scaling_mean": means,
                "scaling_variance": variances,
                "logreg_coef": coefs,
            }
        )
        return model_params
