# Custom scikit-learn transformer
#
# Mainly for preprocessing features.

from sklearn.base import BaseEstimator, TransformerMixin


def proportion_nonzero(column):
    """
    Calculate the proportion of nonzero entries in a numpy
    array.

    Testing: not yet tested
    """
    return (column != 0).mean()


class RemoveMajorityZero(BaseEstimator, TransformerMixin):
    def __init__(self, mean_nonzero_threshold):
        """
        Construct a preprocessor that will remove feature
        columns if the proportion of non-zero entries does
        not exceed mean_nonzero_threshold.
        """
        self._columns_to_keep = None
        self.mean_nonzero_threshold = mean_nonzero_threshold

    def fit(self, X, y=None):
        """
        Fit the transformer to the feature matrix X. Stores
        the columns to keep (those where the proportion of
        non-zeros is high enough). Subsequent calls to
        transform will only keep these columns of X.

        Testing: not yet tested
        """
        self._columns_to_keep = []
        for i, column in enumerate(X.T):
            if proportion_nonzero(column) > self.mean_nonzero_threshold:
                self._columns_to_keep.append(i)
        return self

    def transform(self, X, y=None):
        """
        Remove columns from X based on a previous call to fit.
        """
        if self._columns_to_keep is None:
            raise RuntimeError("Cannot transform before fitting. Call fit first.")

        return X[:, self._columns_to_keep]

    def __repr__(self):
        if self._columns_to_keep is None:
            return "RemoveMajorityZero is not fitted yet"
        else:
            return f"RemoveMajorityZero is fitted and will keep columns {self._columns_to_keep}"


if __name__ == "__main__":
    X = 
    t = RemoveMajorityZero(0.1)
    t.fit_transform(X).shape
    t.transform(X).shape
