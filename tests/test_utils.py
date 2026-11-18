import numpy as np
import pandas as pd

from rr_pressure.utils import eb_shrink_adaptive, eb_shrink_rate


def test_shrinkage_pulls_small_samples_toward_mean():
    values = pd.Series([10.0, 2.0])
    counts = pd.Series([40, 400])
    out = eb_shrink_adaptive(values, counts, 120, 350)
    mean = np.average(values, weights=counts)
    assert abs(out.iloc[0] - mean) < abs(values.iloc[0] - mean)


def test_shrink_rate_bounds_and_pooling():
    out = eb_shrink_rate(pd.Series([1, 0, 8]), pd.Series([1, 1, 10]))
    assert ((out >= 0) & (out <= 1)).all()
    assert out.iloc[0] < 1.0 and out.iloc[1] > 0.0
