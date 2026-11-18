"""Shared imports and global settings for every pipeline stage."""
import os
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # headless: figures are saved to disk, never shown
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.model_selection import GroupKFold

from .utils import eb_shrink_adaptive, eb_shrink_rate

warnings.filterwarnings("ignore")

SEED = 42
np.random.seed(SEED)
pd.set_option("display.max_columns", 35)
pd.set_option("display.width", 220)

# Only scikit-learn gradient boosting is used, so results do not depend on optional libraries.
lgb = None


def display(obj):
    """Notebook-style display() for scripts."""
    print(obj)
