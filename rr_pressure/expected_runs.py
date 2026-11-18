"""Out-of-fold expected runs per ball; batter runs above expected and bowler runs saved."""
from .common import *


def run(ctx):
    balls = ctx['balls']

    # CELL 9 — Expected Runs Model & Bowler Runs Saved Above Expected (RSE)
    # Requirement 5: Gradient-boosted out-of-fold predictions incorporating Innings 2 chase context (runs needed, RRR, target)
    # Consistent bowler RSE calculation (wides/noballs included, byes/legbyes excluded)

    legal_mask = (balls['is_legal'] == 1)
    legal_balls = balls[legal_mask].copy()

    legal_balls['over_num']     = (legal_balls['total_legal_balls'] - legal_balls['balls_remaining']) // 6
    legal_balls['wickets_lost'] = 10 - legal_balls['wickets_in_hand']
    legal_balls['runs_needed_exp'] = legal_balls['runs_needed'].fillna(0.0)
    legal_balls['rrr_capped_exp']  = legal_balls['rrr'].fillna(6.0).clip(lower=0.0, upper=36.0)
    legal_balls['target_exp']      = legal_balls['target'].fillna(165.0)

    features_exp = [
        'balls_remaining', 'wickets_in_hand', 'is_ipl', 'innings',
        'over_num', 'cum_team_runs', 'wickets_lost',
        'runs_needed_exp', 'rrr_capped_exp', 'target_exp'
    ]

    X_exp = legal_balls[features_exp].values
    y_exp = legal_balls['bat_runs'].values
    g_exp = legal_balls['match_id'].values

    gkf_exp = GroupKFold(n_splits=5)
    exp_oof_preds = np.zeros(len(X_exp))

    # Out-of-fold match-grouped training (assert zero leakage)
    for tr_idx, val_idx in gkf_exp.split(X_exp, y_exp, groups=g_exp):
        assert len(set(g_exp[tr_idx]).intersection(set(g_exp[val_idx]))) == 0, "Leakage in expected runs model!"
    
        if lgb is not None:
            model_exp = lgb.LGBMRegressor(
                n_estimators=120, max_depth=5, learning_rate=0.08,
                min_child_samples=30, random_state=SEED, n_jobs=-1, verbose=-1
            )
        else:
            model_exp = HistGradientBoostingRegressor(
                max_iter=120, max_depth=5, learning_rate=0.08, random_state=SEED
            )
        model_exp.fit(X_exp[tr_idx], y_exp[tr_idx])
        exp_oof_preds[val_idx] = model_exp.predict(X_exp[val_idx])

    balls['exp_bat_runs'] = np.nan
    balls.loc[legal_mask, 'exp_bat_runs'] = np.clip(exp_oof_preds, a_min=0.0, a_max=6.0)
    # Centre predictions on legal balls (remove systematic bias) and fill non-legal rows with the LEGAL-ball mean
    _bias = balls.loc[legal_mask, 'bat_runs'].mean() - balls.loc[legal_mask, 'exp_bat_runs'].mean()
    balls.loc[legal_mask, 'exp_bat_runs'] = (balls.loc[legal_mask, 'exp_bat_runs'] + _bias).clip(0.0, 6.0)
    balls['exp_bat_runs'] = balls['exp_bat_runs'].fillna(balls.loc[legal_mask, 'bat_runs'].mean())

    # Runs Above Expected (RAE) for Batters
    balls['batter_rae'] = balls['bat_runs'] - balls['exp_bat_runs']

    # Bowler Runs Saved Above Expected (RSE):
    # Expected runs conceded on ball minus ACTUAL runs charged to bowler (bowler_runs)
    # Consistent accounting: bowler_runs includes wides/noballs, excludes byes/leg-byes
    # Legal balls: expected bat runs - runs charged. Wides/no-balls: no expectation exists, so the bowler is simply
    # charged the runs conceded (previously a filled expectation of ~1.36 handed bowlers phantom credit on wides).
    balls['bowler_rse'] = np.where(balls['is_legal'] == 1, balls['exp_bat_runs'] - balls['bowler_runs'], -balls['bowler_runs'])

    print("Out-of-Fold Expected Runs Baseline Engine complete.")
    print(f"Legal-ball Mean Bat Runs: {balls.loc[legal_mask,'bat_runs'].mean():.3f} | Mean Exp Bat Runs: {balls.loc[legal_mask,'exp_bat_runs'].mean():.3f}")
    assert balls['exp_bat_runs'].isna().sum() == 0, "exp_bat_runs has missing values"


    ctx.update({k: v for k, v in locals().items() if k in ['balls']})
    return ctx
