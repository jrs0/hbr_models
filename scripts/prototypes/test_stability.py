import numpy as np
from stability import make_bootstrapped_resamples


def test_bootstrap_resamples():
    """
    Check the the function which creates bootstrapped
    resamples works correctly. Tests that there are the
    correct number of resulting sets, they are the right
    size, and they contain values from the original
    datasets
    
    TODO: this test is more complicated to understand
    than the function itself! fix.
    """
    X = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]])
    y = np.array([0, 1, 2, 3])

    M = 5
    Xm, ym = make_bootstrapped_resamples(X, y, M)

    # Check the number of resampled arrays
    assert len(Xm) == M
    assert len(ym) == M

    # Check dimensions of al the returned arrays
    for X_rs, y_rs in zip(Xm, ym):
        assert X_rs.shape == X.shape
        assert y_rs.shape == y.shape

    # Check that all the values in every resampled
    # (X_rs,y_rs) combination were present in the
    # original (X,y)
    Xy = np.concatenate((X, y.reshape(-1, 1)), axis=1)
    for X_rs, y_rs in zip(Xm, ym):
        Xy_rs = np.concatenate((X_rs, y_rs.reshape(-1, 1)), axis=1)
        for row in Xy_rs:
            assert np.isin(row, Xy).all()
