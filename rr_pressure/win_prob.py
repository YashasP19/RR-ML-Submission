"""Nested match-grouped, calibrated win-probability models (out-of-fold) for innings 1 and 2."""
from .common import *


def run(ctx):
    balls = ctx['balls']

    # CELL 7 — Dual Calibrated Win-Probability Models with Strictly Nested Match-Grouped OOF Validation
    # Requirement 3: Outer CV and Inner Calibration CV are both grouped by match_id to eliminate leakage completely!

    balls['win_prob'] = np.nan

    SEEDS = [42, 7]

    def get_base_classifier(seed=SEED):
        return HistGradientBoostingClassifier(max_iter=150, max_depth=4, learning_rate=0.08, random_state=seed)

    class SeedEnsemble:
        """Average of calibrated models trained with different seeds (variance reduction)."""
        def __init__(self, models): self.models = models
        def predict_proba(self, X): return np.mean([m.predict_proba(X) for m in self.models], axis=0)

    def fit_seed_ensemble(X, y, splits):
        ms = []
        for sd in SEEDS:
            m = CalibratedClassifierCV(estimator=get_base_classifier(sd), method='sigmoid', cv=splits)
            m.fit(X, y); ms.append(m)
        return SeedEnsemble(ms)

    # Helper function for strictly nested out-of-fold calibrated prediction
    def run_nested_oof_calibration(df, features, target_col='batting_team_won', group_col='match_id'):
        X = df[features].values
        y = df[target_col].values
        groups = df[group_col].values
    
        gkf_outer = GroupKFold(n_splits=5)
        oof_preds = np.zeros(len(df))
    
        for fold, (train_idx, val_idx) in enumerate(gkf_outer.split(X, y, groups=groups)):
            # Assert ZERO match leakage between train and validation folds (Requirement 3)
            train_matches = set(groups[train_idx])
            val_matches   = set(groups[val_idx])
            assert len(train_matches.intersection(val_matches)) == 0, f"Outer fold {fold} match leakage detected!"
        
            X_tr, y_tr, g_tr = X[train_idx], y[train_idx], groups[train_idx]
            X_val = X[val_idx]
        
            # Nested Inner GroupKFold calibration on training matches only
            gkf_inner = GroupKFold(n_splits=3)
            inner_splits = list(gkf_inner.split(X_tr, y_tr, groups=g_tr))
        
            cal_m = fit_seed_ensemble(X_tr, y_tr, inner_splits)
            oof_preds[val_idx] = cal_m.predict_proba(X_val)[:, 1]
        
        return np.clip(oof_preds, 0.001, 0.999)

    # --- 1. INNINGS 1 MODEL ---
    inn1_mask = (balls['innings'] == 1)
    inn1_df   = balls[inn1_mask].copy()

    # Advanced cricket state features for Innings 1 (including reduced-over handling & zero-leakage venue par)
    safe_balls_elapsed = (inn1_df['total_legal_balls'] - inn1_df['balls_remaining']).clip(lower=1.0)
    inn1_df['run_rate'] = (inn1_df['cum_team_runs'] / safe_balls_elapsed) * 6.0
    inn1_df['wickets_lost'] = 10 - inn1_df['wickets_in_hand']
    inn1_df['par_diff'] = inn1_df['cum_team_runs'] - (inn1_df['venue_par_score'] * (safe_balls_elapsed / inn1_df['total_legal_balls']))

    features_inn1 = ['balls_remaining', 'wickets_in_hand', 'cum_team_runs', 'is_ipl', 'run_rate', 'wickets_lost', 'par_diff']

    balls.loc[inn1_mask, 'win_prob'] = run_nested_oof_calibration(inn1_df, features_inn1)

    # Fit full Innings 1 model for prospective counterfactual leverage state transitions
    gkf = GroupKFold(n_splits=5)
    cv1_splits = list(gkf.split(inn1_df[features_inn1].values, inn1_df['batting_team_won'].values, groups=inn1_df['match_id'].values))
    cal_model1 = fit_seed_ensemble(inn1_df[features_inn1].values, inn1_df['batting_team_won'].values, cv1_splits)

    # --- 2. INNINGS 2 MODEL ---
    inn2_mask = (balls['innings'] == 2)
    inn2_df   = balls[inn2_mask].copy()

    inn2_df['rrr_capped'] = inn2_df['rrr'].fillna(6.0).clip(lower=0.0, upper=36.0)
    inn2_df['runs_needed_clean'] = inn2_df['runs_needed'].fillna(0.0).clip(lower=0.0)
    inn2_df['rrr_wkts_interaction'] = inn2_df['rrr_capped'] * (10 - inn2_df['wickets_in_hand'])
    inn2_df['urgency'] = (inn2_df['total_legal_balls'] - inn2_df['balls_remaining']) / inn2_df['total_legal_balls']
    inn2_df['runs_per_ball_needed'] = inn2_df['runs_needed_clean'] / inn2_df['balls_remaining'].clip(lower=1.0)

    features_inn2 = [
        'balls_remaining', 'wickets_in_hand', 'runs_needed_clean',
        'rrr_capped', 'is_ipl', 'rrr_wkts_interaction', 'urgency', 'runs_per_ball_needed'
    ]

    balls.loc[inn2_mask, 'win_prob'] = run_nested_oof_calibration(inn2_df, features_inn2)

    cv2_splits = list(gkf.split(inn2_df[features_inn2].values, inn2_df['batting_team_won'].values, groups=inn2_df['match_id'].values))
    cal_model2 = fit_seed_ensemble(inn2_df[features_inn2].values, inn2_df['batting_team_won'].values, cv2_splits)

    # --- 3. HONEST OUT-OF-FOLD EVALUATION & PHASE BREAKDOWN (Requirement 3) ---
    brier_inn1 = brier_score_loss(inn1_df['batting_team_won'], balls.loc[inn1_mask, 'win_prob'])
    loss_inn1  = log_loss(inn1_df['batting_team_won'], balls.loc[inn1_mask, 'win_prob'])

    brier_inn2 = brier_score_loss(inn2_df['batting_team_won'], balls.loc[inn2_mask, 'win_prob'])
    loss_inn2  = log_loss(inn2_df['batting_team_won'], balls.loc[inn2_mask, 'win_prob'])

    total_brier = brier_score_loss(balls['batting_team_won'], balls['win_prob'])
    total_loss  = log_loss(balls['batting_team_won'], balls['win_prob'])

    print("=== STRICT NESTED OUT-OF-FOLD MODEL PERFORMANCE ===")
    print(f"Innings 1 OOF Brier Score: {brier_inn1:.4f} | Log Loss: {loss_inn1:.4f}")
    print(f"Innings 2 OOF Brier Score: {brier_inn2:.4f} | Log Loss: {loss_inn2:.4f}")
    print(f"Overall Match OOF Brier  : {total_brier:.4f} | Log Loss: {total_loss:.4f}")

    # Phase breakdown
    balls['phase'] = pd.cut(
        balls['balls_remaining'],
        bins=[-1, 30, 84, 150],
        labels=['Death (overs 16-20)', 'Middle (overs 7-15)', 'Powerplay (overs 1-6)']
    )
    phase_metrics = balls.groupby('phase').agg(
        brier=('batting_team_won', lambda y: brier_score_loss(y, balls.loc[y.index, 'win_prob'])),
        logloss=('batting_team_won', lambda y: log_loss(y, balls.loc[y.index, 'win_prob'])),
        deliveries=('team_runs', 'count')
    ).reset_index()
    display(phase_metrics)
    assert balls['win_prob'].isna().sum() == 0, "No NaNs allowed in win_prob"


    ctx.update({k: v for k, v in locals().items() if k in ['balls', 'cal_model1', 'cal_model2', 'inn1_mask', 'inn2_mask', 'phase_metrics', 'brier_inn1', 'brier_inn2', 'loss_inn1', 'loss_inn2']})
    return ctx
