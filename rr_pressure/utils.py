"""Shared statistical helpers (Empirical Bayes shrinkage)."""
import numpy as np
import pandas as pd


def eb_shrink_adaptive(values, counts, base_prior=120, min_stable_count=350):
    scale = np.where(counts < min_stable_count, min_stable_count / counts.clip(lower=1), 1.0)
    adaptive_prior = base_prior * scale
    global_mean = np.average(values, weights=counts)
    return (counts * values + adaptive_prior * global_mean) / (counts + adaptive_prior)


def eb_shrink_rate(n_pos, n_tot, k=10):
    """Beta-binomial style shrinkage of a success rate toward the pooled rate (prior strength k innings)."""
    n_pos = pd.Series(n_pos).fillna(0.0); n_tot = pd.Series(n_tot).fillna(0.0)
    g = n_pos.sum() / max(n_tot.sum(), 1.0)
    return (n_pos + k * g) / (n_tot + k)
