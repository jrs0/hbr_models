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

    # X is first 10 columns, y is last column
    num_features = 3
    Xy = np.random.rand(5, num_features + 1)
    X = Xy[:, :-1]
    y = Xy[:, -1]
    print(f"X = {X}")
    print(f"y = {y}")

    M = 5
    Xm, ym = make_bootstrapped_resamples(X, y, M)

    print(f"X0 = {Xm[0]}")
    print(f"y0 = {ym[0]}")

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
    for X_rs, y_rs in zip(Xm, ym):
        Xy_rs = np.column_stack((X, y))
        assert np.all(
            [(row in Xy) for row in Xy_rs]
        ), "Expected all rows to come from original dataset"
