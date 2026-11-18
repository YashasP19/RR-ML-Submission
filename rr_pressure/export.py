"""Writes results/metrics.json: headline numbers the web app displays."""
import json

from .common import *


def run(ctx):
    OUT_DIR = ctx["OUT_DIR"]
    profile = ctx["profile"]
    summary = ctx["summary_table"]
    normal, high = profile.iloc[0], profile.iloc[1]
    hi = summary[summary["is_pressure"].str.startswith("High")].iloc[0]
    lo = summary[summary["is_pressure"].str.startswith("Normal")].iloc[0]
    metrics = {
        "matches": int(len(ctx["eligible_matches"])),
        "deliveries": int(len(ctx["balls"])),
        "pressureShare": 0.20,
        "bootstrapResamples": 500,
        "winProbBrier": {"innings1": float(ctx["brier_inn1"]), "innings2": float(ctx["brier_inn2"])},
        "swing": {"pressure": float(hi["abs_delta_wp"]), "normal": float(lo["abs_delta_wp"])},
        "profile": {
            "deathOvers": [float(normal.iloc[0]), float(high.iloc[0])],
            "closeContest": [float(normal["Share with WP in 25-75%"]), float(high["Share with WP in 25-75%"])],
        },
        "reliability": {
            "batterStrikeRate": float(ctx["r_full_sr"]),
            "batterWpa": float(ctx["r_full_wpa"]),
            "bowlerEconomy": float(ctx["r_full_ec"]),
        },
    }
    with open(os.path.join(OUT_DIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print("Wrote metrics.json", metrics)
    return ctx
