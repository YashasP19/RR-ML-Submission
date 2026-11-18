"""Pre-ball leverage index, pressure flag, win-probability-added attribution and the CPI cross-check."""
from .common import *


def run(ctx):
    balls = ctx['balls']
    cal_model1 = ctx['cal_model1']
    cal_model2 = ctx['cal_model2']
    inn1_mask = ctx['inn1_mask']
    inn2_mask = ctx['inn2_mask']

    # CELL 8 — Pre-Ball Leverage Index (Empirical Outcomes) & WPA Separation
    # Requirement 2: Empirical phase-based transition probabilities, top 20% legal delivery threshold, hopeless state diagnostic
    # Requirement 4: Explicit separation of striker, non-striker, and bowler WPA with innings reconciliation assertion

    legal_balls = balls[balls['is_legal'] == 1].copy()

    # Compute Empirical Outcome Probabilities by Phase directly from data (Requirement 2)
    phase_outcomes = legal_balls.groupby('phase').agg(
        n=('team_runs', 'count'),
        p_dot=('is_dot', 'mean'),
        p_wicket=('is_wicket_flag', 'mean'),
        p_boundary=('bat_runs', lambda r: np.mean(r.isin([4, 5, 6]))),
    ).reset_index()
    phase_outcomes['p_run'] = (1.0 - phase_outcomes['p_dot'] - phase_outcomes['p_wicket'] - phase_outcomes['p_boundary']).clip(lower=0.0)
    prob_dict = phase_outcomes.set_index('phase')[['p_dot', 'p_run', 'p_boundary', 'p_wicket']].to_dict('index')

    print("=== EMPIRICALLY DERIVED PHASE TRANSITION PROBABILITIES ===")
    display(phase_outcomes)

    # Vectorized true expected swing simulator
    def compute_empirical_preball_li(df, model, innings_num):
        b_rem = (df['balls_remaining'].fillna(60) - 1).clip(lower=0).values
        w_hand = df['wickets_in_hand'].fillna(10).values
        ipl = df['is_ipl'].fillna(0).values
        tot_b = df['total_legal_balls'].fillna(120).values
    
        if innings_num == 1:
            cum_r = df['cum_team_runs'].fillna(0).values
            safe_el = np.clip(tot_b - b_rem, 1.0, None)
            v_par = df['venue_par_score'].fillna(165.0).values
        
            def s1(b, w, r):
                se = np.clip(tot_b - b, 1.0, None)
                rr = (r / se) * 6.0
                pd_ = r - (v_par * (se / tot_b))
                return np.column_stack([b, w, r, ipl, rr, 10 - w, pd_])
            
            s_0 = s1(b_rem, w_hand, cum_r)
            s_1 = s1(b_rem, w_hand, cum_r + 1)
            s_4 = s1(b_rem, w_hand, cum_r + 4)
            s_w = s1(b_rem, np.clip(w_hand - 1, 0, 10), cum_r)
            s_now = s1(df['balls_remaining'].fillna(60).values, w_hand, cum_r)
        else:
            r_nd = df['runs_needed'].fillna(0.0).clip(lower=0.0).values
            def s2(b, w, r):
                r_c = np.clip(r, 0.0, None)
                safe_ov = np.clip(b / 6.0, 1.0 / 6.0, None)
                rrr_c = np.clip(np.where(b > 0, r_c / safe_ov, 36.0), 0.0, 36.0)
                inter = rrr_c * (10.0 - w)
                urg = (tot_b - b) / tot_b
                rpb = r_c / np.clip(b, 1.0, None)
                return np.column_stack([b, w, r_c, rrr_c, ipl, inter, urg, rpb])
            
            s_0 = s2(b_rem, w_hand, r_nd)
            s_1 = s2(b_rem, w_hand, r_nd - 1)
            s_4 = s2(b_rem, w_hand, r_nd - 4)
            s_w = s2(b_rem, np.clip(w_hand - 1, 0, 10), r_nd)
            s_now = s2(df['balls_remaining'].fillna(60).values, w_hand, r_nd)
        
        p0 = model.predict_proba(s_0)[:, 1]
        p1 = model.predict_proba(s_1)[:, 1]
        p4 = model.predict_proba(s_4)[:, 1]
        pw = model.predict_proba(s_w)[:, 1]
        # FIX 2: baseline and counterfactuals come from the SAME model, so model offset cancels
        p_now = model.predict_proba(s_now)[:, 1]
    
        # Weight swings by phase-specific empirical outcome probabilities
        phases = df['phase'].values
        p_dot_arr = np.array([prob_dict.get(ph, {}).get('p_dot', 0.38) for ph in phases])
        p_run_arr = np.array([prob_dict.get(ph, {}).get('p_run', 0.35) for ph in phases])
        p_bnd_arr = np.array([prob_dict.get(ph, {}).get('p_boundary', 0.18) for ph in phases])
        p_wkt_arr = np.array([prob_dict.get(ph, {}).get('p_wicket', 0.09) for ph in phases])
    
        expected_swing = (
            p_dot_arr * np.abs(p0 - p_now) +
            p_run_arr * np.abs(p1 - p_now) +
            p_bnd_arr * np.abs(p4 - p_now) +
            p_wkt_arr * np.abs(pw - p_now)
        )
        return np.nan_to_num(expected_swing, nan=0.01)

    balls['preball_li'] = np.nan
    balls.loc[inn1_mask, 'preball_li'] = compute_empirical_preball_li(balls[inn1_mask], cal_model1, 1)
    balls.loc[inn2_mask, 'preball_li'] = compute_empirical_preball_li(balls[inn2_mask], cal_model2, 2)
    balls['preball_li'] = balls['preball_li'].fillna(balls['preball_li'].median())
    assert balls['preball_li'].isna().sum() == 0, "No NaNs permitted in preball_li"

    # Reconciled High Pressure Definition: STRICT Top 20% Pre-Ball Leverage on Legal Deliveries (Requirement 2)
    # FIX 3: threshold set per innings (top 20% of legal balls WITHIN each innings) so the weaker
    #        innings-1 win-prob model cannot starve/flood pressure; overall legal share stays 20%.
    # FIX 1: the flag is applied to EVERY delivery (incl. wides/no-balls) at/above the threshold,
    #        so extras bowled in high-leverage states are no longer dumped into the 'normal' bucket.
    PRESSURE_PER_INNINGS = True
    _legal = balls['is_legal'] == 1
    if PRESSURE_PER_INNINGS:
        _thr = balls[_legal].groupby('innings')['preball_li'].quantile(0.80)
        balls['pressure_threshold'] = balls['innings'].map(_thr)
    else:
        balls['pressure_threshold'] = balls.loc[_legal, 'preball_li'].quantile(0.80)
    balls['is_pressure'] = (balls['preball_li'] >= balls['pressure_threshold']).astype(int)
    print("Pressure share of legal balls by innings:", balls[_legal].groupby('innings')['is_pressure'].mean().round(3).to_dict())
    print("Pressure share of wides/no-balls:", round(balls[~_legal]['is_pressure'].mean(), 3))

    # Assertion confirming exactly 20.0% legal pressure share (Requirement 2)
    flagged_share = balls[balls['is_legal'] == 1]['is_pressure'].mean()
    print(f"Reconciled Pressure Delivery Share on Legal Deliveries: {flagged_share:.2%}")
    assert abs(flagged_share - 0.20) < 0.01, f"Expected 20% pressure share, got {flagged_share:.4f}"

    # Hopeless / Decided States Diagnostic (Requirement 2)
    hopeless_share = balls[balls['is_pressure'] == 1]['win_prob'].map(lambda p: (p < 0.05) or (p > 0.95)).mean()
    mean_rrr_p = balls[(balls['is_pressure'] == 1) & (balls['innings'] == 2)]['rrr'].mean()
    print(f"Diagnostic: Decided/Hopeless balls in High Pressure (WP < 5% or > 95%): {hopeless_share:.2%}")
    print(f"Diagnostic: Mean Required Run Rate in 2nd Innings High Pressure: {mean_rrr_p:.2f}")

    # First-Innings Terminal Transition & Team WPA (Requirement 3 & 4)
    balls['win_prob_next'] = balls.groupby(['match_id', 'innings'])['win_prob'].shift(-1)

    # Correct Innings 1 terminal transition from post-delivery defending state
    last1 = inn1_mask & balls['win_prob_next'].isna()
    if last1.sum() > 0:
        ends1 = balls[last1].copy()
        f_runs = ends1['cum_team_runs'] + ends1['team_runs']
        f_wkts = np.clip(ends1['wickets_in_hand'] - ends1['any_wicket'], 0, 10)
        s_end = np.column_stack([
            np.zeros(len(ends1)), f_wkts, f_runs, ends1['is_ipl'],
            (f_runs / 20.0), 10 - f_wkts, f_runs - ends1['venue_par_score']
        ])
        balls.loc[last1, 'win_prob_next'] = cal_model1.predict_proba(s_end)[:, 1]

    last2 = inn2_mask & balls['win_prob_next'].isna()
    balls.loc[last2, 'win_prob_next'] = balls.loc[last2, 'batting_team_won'].astype(float)
    balls['win_prob_next'] = balls['win_prob_next'].fillna(balls['win_prob'])

    # Signed Team-Level Swing
    balls['team_wpa'] = balls['win_prob_next'] - balls['win_prob']

    # Individual WPA Separation (Requirement 4)
    # Striker gets WPA on their own outcomes; Non-striker gets charged if they were run out!
    balls['striker_wpa'] = np.where(
        balls['is_non_striker_out'] == 1,
        0.0, # Striker is NOT charged for non-striker's run out
        balls['team_wpa']
    )
    balls['non_striker_wpa'] = np.where(
        balls['is_non_striker_out'] == 1,
        balls['team_wpa'], # Non-striker absorbs the negative wicket swing
        0.0
    )
    balls['bowler_wpa'] = np.where(
        balls['dismissal_type_clean'] == 'RunOut',
        0.0, # Bowler does NOT take positive WPA credit for fielding run-outs
        -balls['team_wpa']
    )

    balls['batter_wpa'] = balls['striker_wpa']

    # WPA Reconciliation Assertion (Requirement 4)
    batting_side_wpa = (balls['striker_wpa'] + balls['non_striker_wpa']).sum()
    total_team_wpa   = balls['team_wpa'].sum()
    assert np.isclose(batting_side_wpa, total_team_wpa, atol=1e-5), "Batting side WPA does not reconcile with Team WPA!"
    # Non-trivial check: per-innings team WPA must telescope to (final next-WP - initial WP)
    _g = balls.groupby(['match_id', 'innings'])
    _chk = _g['team_wpa'].sum() - (_g['win_prob_next'].last() - _g['win_prob'].first())
    assert np.allclose(_chk, 0, atol=1e-6), "Per-innings WPA does not telescope!"
    print("WPA Separation & telescoping reconciliation assertions passed successfully!")

    # Summary Table (assert zero NaNs in table)
    summary_table = balls.groupby('is_pressure').agg(
        deliveries=('team_runs', 'count'),
        mean_preball_li=('preball_li', 'mean'),
        abs_delta_wp=('team_wpa', lambda x: np.mean(np.abs(x))),
        boundary_pct=('bat_runs', lambda x: 100.0 * np.mean(
            (balls.loc[x.index, 'is_four'].astype(str).str.lower() == 'true') |
            (balls.loc[x.index, 'is_six'].astype(str).str.lower() == 'true')
        )),
        wicket_pct=('any_wicket', lambda x: 100.0 * np.mean(x)),
        mean_rrr=('rrr', 'mean')
    ).reset_index()
    summary_table['is_pressure'] = summary_table['is_pressure'].map({0: 'Normal Situation (80%)', 1: 'High Pressure (Top 20%)'})
    assert summary_table.isna().sum().sum() == 0, "No NaNs allowed in pressure validation table"
    display(summary_table)


    # CELL 8b — Cricket Pressure Index (CPI): explainable cross-check of the leverage-based flag
    _b = balls
    _death = (_b['phase'] == 'Death (overs 16-20)')
    _lowW  = _b['wickets_in_hand'] <= 4
    _close = (_b['win_prob'] - 0.5).abs() <= 0.25
    _elapsed = (_b['total_legal_balls'] - _b['balls_remaining'])
    _rate  = np.where(_b['innings'] == 2, _b['rrr'].fillna(0) >= 9.5,
                      _b['cum_team_runs'] < _b['venue_par_score'] * _elapsed / _b['total_legal_balls'])
    balls['cpi'] = _death.astype(int) + _lowW.astype(int) + _close.astype(int) + pd.Series(_rate, index=_b.index).astype(int)

    _L = balls[balls['is_legal'] == 1]
    rho_cpi, _ = stats.spearmanr(_L['cpi'], _L['preball_li'])
    print(f"Spearman(CPI, pre-ball leverage) on legal balls: {rho_cpi:.3f}")

    profile = pd.DataFrame({
        'Share of balls in death overs': _L.groupby('is_pressure')['phase'].apply(lambda x: (x == 'Death (overs 16-20)').mean()),
        'Share with <=4 wickets in hand': _L.groupby('is_pressure')['wickets_in_hand'].apply(lambda x: (x <= 4).mean()),
        'Share with WP in 25-75%': _L.groupby('is_pressure')['win_prob'].apply(lambda x: ((x - 0.5).abs() <= 0.25).mean()),
        'Share in 2nd innings': _L.groupby('is_pressure')['innings'].apply(lambda x: (x == 2).mean()),
        'Mean CPI (0-4)': _L.groupby('is_pressure')['cpi'].mean(),
        'Share CPI >= 3': _L.groupby('is_pressure')['cpi'].apply(lambda x: (x >= 3).mean()),
    })
    profile.index = profile.index.map({0: 'Normal (80%)', 1: 'High Pressure (20%)'})
    print("\nPressure vs ordinary situations (legal balls):")
    display(profile.round(3))


    ctx.update({k: v for k, v in locals().items() if k in ['balls', 'phase_outcomes', 'prob_dict', 'summary_table', 'profile']})
    return ctx
