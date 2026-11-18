"""Runs the full pipeline, stage by stage, passing a shared context dict along."""
import importlib
import os
import time

STAGES = [
    "data_prep",      # load + scope + delivery accounting
    "game_state",     # innings state engine
    "win_prob",       # calibrated win-probability models
    "pressure",       # leverage index + pressure flag + WPA
    "expected_runs",  # runs-above-expected baseline
    "batters",        # batter ratings
    "bowlers",        # bowler ratings
    "bootstrap",      # 500-resample rank stability
    "visuals",        # plots
    "report",         # baseline top-10 tables
    "validation",     # reliability + sensitivity
    "consensus",      # final submission ranking
    "export",         # metrics for the web app
]


def run_all(data_dir="data", out_dir="results", stages=None):
    os.makedirs(out_dir, exist_ok=True)
    ctx = {"DATA_DIR": data_dir, "OUT_DIR": out_dir}
    for name in stages or STAGES:
        t0 = time.time()
        print(f"\n{'=' * 80}\nSTAGE: {name}\n{'=' * 80}", flush=True)
        ctx = importlib.import_module(f"rr_pressure.{name}").run(ctx)
        print(f"[{name}] done in {time.time() - t0:.0f}s", flush=True)
    return ctx
