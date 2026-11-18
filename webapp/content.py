"""Static, human-written content for the method section (numbers come from results/metrics.json)."""

# Numbers on the card backs come from the outputs of Final_v2.ipynb. Update them if the pipeline is rerun.
STEPS = [
    {"title": "Scope the data", "text": "IPL plus T20Is between the 12 full-member nations, from January 2022.", "why": "Weaker opponents inflate stats, so we compare like with like.", "evidence": ["883 matches in the files, 761 kept: 362 IPL and 399 T20Is.", "180,345 deliveries scored."]},
    {"title": "Win probability on every ball", "text": "A calibrated model for each innings, tested on matches it never saw.", "why": "Pressure needs an honest chance of winning at every ball.", "evidence": ["Chase model Brier score 0.13, so it is accurate.", "First innings 0.23, near a coin flip, so cut-offs are set per innings."]},
    {"title": "Define pressure", "text": "Balls where the next delivery could swing win probability the most.", "why": "Fixed rules treat a hopeless chase like a tight one.", "evidence": ["Pressure balls swing 2.8x more (0.031 against 0.011).", "82% are in close contests (25% to 75% win chance).", "Only 0.6% are nearly decided."]},
    {"title": "Measure each player", "text": "Win probability added, runs above expected, dot balls and consistency.", "why": "Twelve runs in a tight chase beat twelve in a dead game.", "evidence": ["22.8% of wides and no-balls fall in pressure states and are counted.", "Runs above expected compares each ball with the match situation."]},
    {"title": "Compare fairly", "text": "Small samples are shrunk, and elevation compares pressure with normal play.", "why": "Small samples flatter players, and elevation shows who steps up.", "evidence": ["76 batters and 31 bowlers cleared the cut-offs.", "Abhishek Sharma: top runs above expected, elevation -2.63. Klaasen: +16.06."]},
    {"title": "Combine and stress-test", "text": "A five-part score, then bootstrap and cut-off checks give a consensus.", "why": "One metric can be luck, so we blend five and test them.", "evidence": ["Alternative weightings keep 7 to 10 of the top 10.", "Sunil Narine, 2nd on raw score, misses the top 10: eligible in under 70% of resamples."]},
]

LIMITS = [
    "Ranks 1 to 3 in each list are firm. Ranks 4 to 10 are close, so their order could shift under another reasonable choice.",
    "Opposition strength is not adjusted. All deliveries between full members count equally.",
    "Pressure comes from a model, so a different win-probability model could move some names.",
    "Some players are strong in only one competition. Players with thin samples are flagged.",
    "Reliability is moderate, so the order within the lower half of each list should be read as close.",
]

UNIQUE = [
    {"concept": "Gradient boosting + calibration", "title": "Pressure is measured", "text": "Next-ball win-probability swing, not fixed rules.", "detail": "Pressure balls swing win probability 2.8x more than ordinary balls."},
    {"concept": "Out-of-fold validation", "title": "No data leakage", "text": "Models never see the match they score.", "detail": "Folds are grouped by match, with a check that none overlap."},
    {"concept": "Empirical Bayes shrinkage", "title": "Fair to small samples", "text": "Thin samples are pulled toward the average.", "detail": "Minimum pressure balls: 150 for batters, 250 for bowlers."},
    {"concept": "Runs above expected model", "title": "Judged against own level", "text": "Rewards players who step up.", "detail": "Elevation compares pressure with normal play: Klaasen +16.06."},
    {"concept": "Bootstrap resampling", "title": "Honest about uncertainty", "text": "Every player gets a top-10 chance.", "detail": "500 match-level resamples: Tim David stays in the top 10 in 88%."},
    {"concept": "Consensus ranking", "title": "Stable final order", "text": "Averaged across cut-offs and resamples.", "detail": "Under 70% eligible: out of the top 10. Under 75%: out of the top 3."},
]
