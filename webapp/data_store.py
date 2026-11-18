"""Loads the pipeline's result files and exposes typed, searchable player records."""
import csv
import json
import os
import re
import threading

LOW_ELIGIBILITY = 0.70  # flagged when eligible in under 70% of bootstrap resamples

# CSV column -> API field, per player type
FIELDS = {
    "batters": {
        "p_balls": "pressureBalls", "p_sr": "strikeRate", "p_rae100": "rae100", "p_wpa100": "wpa100",
        "delta_rae": "elevation", "p_pos_rate": "consistency",
    },
    "bowlers": {
        "p_balls": "pressureBalls", "p_econ": "economy", "p_dot_pct": "dotPct", "p_wpa_ov": "wpaPerOver",
        "p_rse_ov": "rsePerOver", "delta_rse": "elevation", "p_pos_rate": "consistency",
    },
}
COMMON = {"Rank": "rank", "consensus": "consensusScore", "final_rank": "baselineRank",
          "boot_median": "bootstrapMedianRank", "p_elig": "pEligible", "p_top10_uncond": "pTop10"}


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f


class ResultsStore:
    def __init__(self, results_dir):
        self.dir = results_dir
        self._lock = threading.Lock()
        self._cache = {}

    def _load_players(self, kind):
        path = os.path.join(self.dir, f"players_{kind}.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} not found. Run the pipeline first (python run_pipeline.py).")
        rows = []
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rec = {"name": r["player_name"], "slug": slugify(r["player_name"])}
                for col, field in {**COMMON, **FIELDS[kind]}.items():
                    rec[field] = _num(r.get(col))
                for key in ("rank", "baselineRank", "pressureBalls"):
                    if rec.get(key) is not None:
                        rec[key] = int(rec[key])
                rec["lowEligibility"] = rec["pEligible"] is not None and rec["pEligible"] < LOW_ELIGIBILITY
                rows.append(rec)
        rows.sort(key=lambda x: x["rank"])
        return rows

    def players(self, kind):
        if kind not in FIELDS:
            raise KeyError(kind)
        with self._lock:
            if kind not in self._cache:
                self._cache[kind] = self._load_players(kind)
            return self._cache[kind]

    def top(self, kind, n=10):
        return self.players(kind)[:n]

    def search(self, kind, q="", sort="rank", limit=100):
        rows = self.players(kind)
        if q:
            ql = q.lower()
            rows = [r for r in rows if ql in r["name"].lower()]
        if sort != "rank":
            rows = sorted(rows, key=lambda r: (r.get(sort) is None, -(r.get(sort) or 0)))
        return rows[:limit]

    def player(self, kind, slug):
        return next((r for r in self.players(kind) if r["slug"] == slug), None)

    def metrics(self):
        with self._lock:
            if "metrics" not in self._cache:
                path = os.path.join(self.dir, "metrics.json")
                if not os.path.exists(path):
                    raise FileNotFoundError(f"{path} not found. Run the pipeline first.")
                with open(path, encoding="utf-8") as f:
                    self._cache["metrics"] = json.load(f)
            return self._cache["metrics"]
