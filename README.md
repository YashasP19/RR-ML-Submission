# Pressure Players: the most reliable batters and bowlers under pressure in T20 cricket

**SupeRR Selector Season 2, Round 1.** A data-driven system that rates IPL and full-member T20I players on how they perform in high-pressure moments, compared with their own usual level, and ranks the ten most reliable batters and bowlers.

| | |
|---|---|
| **Live dashboard** | https://rr-pressure-players.onrender.com |
| **Methodology report (PDF)** | [`reports/SupeRR_Selector_Season2_Round1_Methodology_Report.pdf`](reports/SupeRR_Selector_Season2_Round1_Methodology_Report.pdf) |
| **Analysis notebook** | [`Final_v2.ipynb`](Final_v2.ipynb) (full narrated run with outputs) |

> The free Render instance sleeps when idle, so the first load of the live link can take about a minute.

## Final top 10

| # | Batters | Bowlers |
|---|---|---|
| 1 | Tim David | Josh Hazlewood |
| 2 | Heinrich Klaasen | Akeal Hosein |
| 3 | Abhishek Sharma | Kuldeep Yadav |
| 4 | Cameron Green | Jasprit Bumrah |
| 5 | Daryl Mitchell | Mohammed Siraj |
| 6 | Yashasvi Jaiswal | Rashid Khan |
| 7 | Rinku Singh | Varun Chakravarthy |
| 8 | David Miller | Kagiso Rabada |
| 9 | Shubman Gill | Trent Boult |
| 10 | Prabhsimran Singh | Maheesh Theekshana |

The order is a consensus of the baseline score, the bootstrap median rank and the ranks under other eligibility cut-offs. Ranks 1 to 3 in each list are firm; ranks 4 to 10 are close. The full tables, including each player's top-10 chance, are in [`results/`](results/).

## Key numbers

- **761 matches** (362 IPL, 399 full-member T20Is) and **180,345 deliveries**, from January 2022.
- Pressure balls swing win probability **2.8x** more than ordinary balls (0.031 against 0.011).
- Out-of-fold win-probability Brier score: **0.132** in chases, **0.227** in the first innings.
- Split-half reliability (Spearman-Brown): batter strike rate 0.57, batter win probability added 0.41, bowler economy 0.63.
- **500** match-level bootstrap resamples give every player a top-10 chance.

## How it works

1. **Scope.** IPL plus T20Is between the 12 ICC full members, from 2022-01-01. Abandoned matches and super overs are excluded.
2. **Win probability.** Gradient-boosted models (scikit-learn), one for each innings, calibrated and scored out-of-fold with folds grouped by match.
3. **Pressure.** The expected swing in win probability on the next ball across dot, run, boundary and wicket outcomes, weighted by phase. The top 20% of balls in each innings are pressure balls.
4. **Player metrics.** Win probability added, runs above expected (batters), runs saved above expected (bowlers), strike rate or economy, dot balls, and consistency.
5. **Fair comparison.** Empirical Bayes shrinkage for small samples, elevation against each player's own normal level, and minimum pressure balls (150 for batters, 250 for bowlers).
6. **Ranking.** A weighted five-part score, then a consensus with bootstrap and eligibility-cut-off ranks. Players eligible in under 70% of resamples cannot be in the top 10, and under 75% cannot be in the top 3.

The full reasoning, tables and limitations are in the [methodology report](reports/SupeRR_Selector_Season2_Round1_Methodology_Report.pdf).

## Project structure

```
.
├── Final_v2.ipynb              # the full analysis as one narrated notebook, with outputs
├── run_pipeline.py             # runs the same pipeline from the command line
├── rr_pressure/                # ML pipeline, one module per stage
│   ├── data_prep.py            #   load, scope, delivery accounting
│   ├── game_state.py           #   score, wickets, balls left, target, required rate, venue par
│   ├── win_prob.py             #   calibrated win-probability models
│   ├── pressure.py             #   leverage, pressure flag, win probability added
│   ├── expected_runs.py        #   runs above / saved above expected
│   ├── batters.py, bowlers.py  #   metrics, shrinkage, elevation, scores
│   ├── bootstrap.py            #   500-resample match-level bootstrap
│   ├── validation.py           #   reliability and sensitivity tests
│   ├── consensus.py            #   final ranking and submission CSVs
│   ├── export.py               #   headline metrics for the web app
│   └── utils.py, common.py, pipeline.py
├── webapp/                     # Flask app deployed on Render
│   ├── __init__.py, routes.py, data_store.py, content.py, wsgi.py
│   ├── templates/              #   page templates
│   └── static/                 #   CSS, JS, logo
├── results/                    # pipeline outputs the web app serves
├── reports/                    # methodology report PDF, figures and builder assets
├── scripts/build_report.py     # regenerates the PDF from results/
├── tests/                      # unit tests for the pipeline helpers and the API
├── data/                       # organiser CSVs (not committed, see data/README.md)
├── reference/                  # problem statement
├── render.yaml, Procfile, requirements-web.txt   # deployment
└── requirements.txt            # everything needed to run, test and build the report
```

## Quick start

Python 3.12 or newer is recommended.

```bash
git clone https://github.com/YashasP19/RR-ML-Submission.git
cd RR-ML-Submission
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Run the pipeline

The organiser's data files are not included. Place `ball_by_ball.csv`, `matches.csv`, `competitions.csv`, `teams.csv`, `playing_eleven.csv` and `competition_team_player_mapping.csv` in `data/` (see [`data/README.md`](data/README.md)), then:

```bash
python run_pipeline.py --data-dir data --out-dir results
```

A full run takes several minutes (win-probability models and 500 bootstrap resamples). Only scikit-learn gradient boosting is used with fixed seeds, so results are the same on any machine, and rerunning the modular pipeline gives output identical to the notebook.

### Run the tests

```bash
python -m pytest -q tests
```

### Run the web app locally

```bash
gunicorn webapp.wsgi:app -b 127.0.0.1:8000
# open http://127.0.0.1:8000
```

### Rebuild the report PDF

```bash
python scripts/build_report.py
```

## Deployment

The site is a Flask app served by gunicorn. It only reads the files in `results/`, so the deployed service does not need the raw data or the ML libraries.

**Live:** https://rr-pressure-players.onrender.com (Render, free plan, Python 3.12).

### Deploy your own copy on Render

1. Push this repository to GitHub. The `results/` folder must be committed.
2. In the [Render dashboard](https://dashboard.render.com) choose **New**, then **Blueprint**, and connect the repository.
3. Render reads [`render.yaml`](render.yaml) and creates the `rr-pressure-players` web service. Click **Apply**.
4. Wait for the build (about a minute). Open the service URL, then check `/api/health` returns `{"status":"ok"}`.

To create the service by hand instead, choose **New**, then **Web Service**, and use:

| Setting | Value |
|---|---|
| Runtime | Python 3 |
| Build command | `pip install -r requirements-web.txt` |
| Start command | `gunicorn webapp.wsgi:app --workers 2 --threads 4 --timeout 60` |
| Health check path | `/api/health` |
| Environment | `PYTHON_VERSION=3.12.7` |

The [`Procfile`](Procfile) has the same start command for Heroku-style platforms.

### Updating the live site

Rerun the pipeline, commit the new files in `results/`, and push to `main`. Render redeploys automatically.

### Configuration

| Variable | Purpose | Default |
|---|---|---|
| `RESULTS_DIR` | Folder the app reads results from | `./results` |
| `PYTHON_VERSION` | Python version on Render | `3.12.7` |

## API

| Endpoint | Returns |
|---|---|
| `GET /api/health` | Service status (`503` if result files are missing) |
| `GET /api/rankings/<batters\|bowlers>?limit=10` | Consensus top players |
| `GET /api/players/<kind>?q=&sort=&limit=` | All eligible players, searchable and sortable (`rank`, `pressureBalls`, `pTop10`, `elevation`, `consistency`) |
| `GET /api/players/<kind>/<slug>` | One player |
| `GET /api/metrics` | Headline numbers (pressure swing, reliability, counts) |
| `GET /api/method` | Method steps shown on the site |

## Limitations

- Opposition strength is not adjusted; all deliveries between full members count equally.
- Pressure is defined through a model, so a different win-probability model could move some names.
- The first-innings model is weak (Brier 0.227), so first-innings pressure labels are noisier.
- Reliability is moderate, so the order within ranks 4 to 10 should be read as close.
- Some players rest on one competition only and are flagged in the report.

## Notes

- The competition data and problem statement belong to the SupeRR Selector organisers.
- The Rajasthan Royals name and logo belong to their owners and are used here only to present this challenge entry.
