# RR ML Challenge: SupeRR Selector Season 2, Round 1

Which batters and bowlers deliver when the match is on the line? This project rates players on how they perform in high-pressure T20 situations (IPL and full-member T20Is, 2022 onwards), compared with their own usual level.

**Final output:** `results/top10_batters_consensus.csv` and `results/top10_bowlers_consensus.csv`.

## Project layout

```
.
├── Final_v2.ipynb          # the full analysis as one narrated notebook, with outputs
├── run_pipeline.py         # runs the same pipeline from the command line
├── rr_pressure/            # ML pipeline, one module per stage
│   ├── data_prep.py        #   load, scope (IPL + full-member T20Is), delivery accounting
│   ├── game_state.py       #   score, wickets, balls left, target, required rate, venue par
│   ├── win_prob.py         #   calibrated win-probability models, folds grouped by match
│   ├── pressure.py         #   pre-ball leverage, pressure flag, win probability added, CPI check
│   ├── expected_runs.py    #   runs above expected / runs saved above expected
│   ├── batters.py, bowlers.py   # metrics, shrinkage, elevation, composite scores
│   ├── bootstrap.py        #   500-resample match-level bootstrap
│   ├── validation.py       #   split-half reliability and sensitivity tests
│   ├── consensus.py        #   final consensus ranking, submission CSVs, full player tables
│   ├── export.py           #   headline metrics for the web app
│   └── utils.py, common.py, pipeline.py
├── webapp/                 # Flask app deployed on Render
│   ├── __init__.py         #   app factory
│   ├── routes.py           #   page + JSON API
│   ├── data_store.py       #   reads results/ into typed player records
│   ├── content.py          #   method text
│   ├── templates/          #   base.html, index.html
│   ├── static/css|js|img   #   Rajasthan Royals-style UI (add img/rr-logo.png)
│   └── wsgi.py             #   gunicorn entry point
├── data/                   # organiser CSVs (not committed, see data/README.md)
├── results/                # pipeline outputs the web app serves
├── tests/                  # unit tests for the pipeline helpers and the API
├── render.yaml, Procfile, requirements-web.txt   # deployment
├── requirements.txt        # full pipeline dependencies
└── reference/              # problem statement
```

## Run the pipeline

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# put the CSV files in ./data, then:
python run_pipeline.py --data-dir data --out-dir results
python -m pytest -q tests
```

The full run takes several minutes (win-probability models and 500 bootstrap resamples). Only scikit-learn gradient boosting is used, so results are the same on any machine.

## Run the web app locally

```bash
pip install -r requirements-web.txt
gunicorn webapp.wsgi:app          # or: flask --app webapp.wsgi run
# http://127.0.0.1:8000
```

API: `/api/health`, `/api/rankings/<batters|bowlers>?limit=10`, `/api/players/<kind>?q=&sort=&limit=`, `/api/players/<kind>/<slug>`, `/api/metrics`, `/api/method`.

## Deploy on Render

1. Push the repo to GitHub (the `results/` folder must be committed, the app only reads it).
2. On Render choose New, then Blueprint, and select the repo. `render.yaml` sets the build command, start command and health check.
3. Or create a Web Service by hand: build `pip install -r requirements-web.txt`, start `gunicorn webapp.wsgi:app`, health check path `/api/health`.

The web service does not need the raw data or the ML libraries. To update the rankings, rerun the pipeline, commit the new `results/` files and push.

## Method in brief

1. **Scope:** IPL plus T20Is between the 12 full-member nations, from 2022-01-01. Abandoned matches and super overs are dropped.
2. **Win probability** on every ball from calibrated gradient-boosted models for each innings, scored out-of-fold with folds grouped by match.
3. **Pressure** is the pre-ball expected swing in win probability across dot, run, boundary and wicket outcomes, weighted by phase. The top 20% of balls in each innings are pressure balls.
4. **Player metrics:** win probability added, runs above expected, strike rate or economy, dot balls, and the share of innings or spells with a positive impact.
5. **Fair comparison:** Empirical Bayes shrinkage, elevation against the player's normal performance, eligibility of 150 pressure balls for batters and 250 for bowlers.
6. **Final order:** a weighted five-part score, then a consensus of the baseline rank, the bootstrap median rank and ranks under other eligibility cutoffs. Players eligible in under 70% of resamples cannot be in the top 10, and under 75% cannot be in the top 3.

## Limitations

Opposition strength is not adjusted. Pressure is defined through a model, so another model could move some names. Ranks 4 to 10 are close. Some players have thin samples in one competition and are flagged.
