"""Bowler pressure metrics, Empirical Bayes shrinkage, elevation and composite score."""
from .common import *


def run(ctx):
    balls = ctx['balls']
    player_name_map = ctx['player_name_map']

    # CELL 11 — Bowler Metrics: Absolute Suppression & Personal Baseline Elevation
    # Requirement 5 & 9: True dot-ball accounting, adaptive EB, 150-ball normal threshold, provisional tags

    def aggregate_bowler_stats(df, label):
        agg_df = df.groupby('bowler_id').agg(
            balls=('is_legal', 'sum'),
            total_balls_all=('team_runs', 'count'),
            runs_conc=('bowler_runs', 'sum'),
            wickets=('is_bowler_wicket', 'sum'),
            dots=('is_dot', 'sum'),
            total_wpa=('bowler_wpa', 'sum'),
            total_rse=('bowler_rse', 'sum')
        ).reset_index()
    
        agg_df[f'{label}_balls']   = agg_df['balls']
        agg_df[f'{label}_overs']   = agg_df['balls'] / 6.0
        agg_df[f'{label}_econ']    = agg_df['runs_conc'] / agg_df[f'{label}_overs'].replace(0, np.nan)
        agg_df[f'{label}_dot_pct'] = 100.0 * agg_df['dots'] / agg_df['balls'].replace(0, np.nan)
        agg_df[f'{label}_wpa_ov']  = agg_df['total_wpa'] / agg_df[f'{label}_overs'].replace(0, np.nan)
        agg_df[f'{label}_rse_ov']  = agg_df['total_rse'] / agg_df[f'{label}_overs'].replace(0, np.nan)
        agg_df[f'{label}_sr']      = agg_df['balls'] / agg_df['wickets'].replace(0, np.nan)
    
        # Consistency: % of spells (with >= 6 legal balls) having net positive WPA
        spell_wpa = df.groupby(['bowler_id', 'match_id']).agg(
            wpa_sum=('bowler_wpa', 'sum'),
            balls_count=('is_legal', 'sum')
        ).reset_index()
        spell_qual = spell_wpa[spell_wpa['balls_count'] >= 6]
        spell_stats = spell_qual.groupby('bowler_id').agg(
            pos_spell_rate=('wpa_sum', lambda x: np.mean(x > 0)),
            wpa_sd=('wpa_sum', 'std'),
            n_inn=('wpa_sum', 'size'),
            n_pos=('wpa_sum', lambda x: int(np.sum(x > 0)))
        ).reset_index()
        agg_df[f'{label}_n_inn'] = agg_df['bowler_id'].map(spell_stats.set_index('bowler_id')['n_inn']).fillna(0)
        agg_df[f'{label}_n_pos'] = agg_df['bowler_id'].map(spell_stats.set_index('bowler_id')['n_pos']).fillna(0)
        agg_df[f'{label}_pos_rate'] = agg_df['bowler_id'].map(spell_stats.set_index('bowler_id')['pos_spell_rate']).fillna(0)
    
        return agg_df[['bowler_id', f'{label}_balls', f'{label}_econ', f'{label}_dot_pct', f'{label}_wpa_ov', f'{label}_rse_ov', f'{label}_sr', f'{label}_pos_rate', f'{label}_n_inn', f'{label}_n_pos']]

    p_bowl = aggregate_bowler_stats(balls[balls['is_pressure'] == 1], 'p')
    n_bowl = aggregate_bowler_stats(balls[balls['is_pressure'] == 0], 'n')

    bowl_stats = p_bowl.merge(n_bowl, on='bowler_id', how='left')
    bowl_stats['player_name'] = bowl_stats['bowler_id'].map(player_name_map)

    # Official Eligibility: >= 250 pressure balls
    bowl_eligible = bowl_stats[bowl_stats['p_balls'] >= 250].copy()

    # Provisional Tagging (Requirement 9: Flag bowlers within 15% of eligibility threshold)
    bowl_eligible['is_provisional'] = np.where(bowl_eligible['p_balls'] < 290, 'Provisional (Near Cutoff)', 'Established')

    # Adaptive Empirical Bayes Shrinkage
    bowl_eligible['p_inv_econ'] = 1.0 / bowl_eligible['p_econ'].replace(0, np.nan)
    bowl_eligible['p_inv_econ_shrunk'] = eb_shrink_adaptive(bowl_eligible['p_inv_econ'], bowl_eligible['p_balls'], base_prior=150, min_stable_count=450)
    bowl_eligible['p_wpa_shrunk']      = eb_shrink_adaptive(bowl_eligible['p_wpa_ov'], bowl_eligible['p_balls'], base_prior=150, min_stable_count=450)
    bowl_eligible['p_rse_shrunk']      = eb_shrink_adaptive(bowl_eligible['p_rse_ov'], bowl_eligible['p_balls'], base_prior=150, min_stable_count=450)
    bowl_eligible['p_dot_shrunk']      = eb_shrink_adaptive(bowl_eligible['p_dot_pct'], bowl_eligible['p_balls'], base_prior=150, min_stable_count=450)

    # Baseline Delta with Minimum Normal-Ball Sample Threshold (Requirement 5 & 10)
    # CHANGE 2: elevation on RSE/over (context-adjusted) - removes the death-over phase confound of raw economy
    bowl_eligible['n_rse_shrunk']      = eb_shrink_adaptive(bowl_eligible['n_rse_ov'].fillna(bowl_eligible['n_rse_ov'].mean()), bowl_eligible['n_balls'].fillna(0), base_prior=150, min_stable_count=450)
    bowl_eligible['delta_rse']         = bowl_eligible['p_rse_shrunk'] - bowl_eligible['n_rse_shrunk']

    bowl_eligible['p_pos_rate_raw'] = bowl_eligible['p_pos_rate']
    bowl_eligible['p_pos_rate'] = eb_shrink_rate(bowl_eligible['p_n_pos'], bowl_eligible['p_n_inn']).values

    # Standardize with Z-scores
    for col in ['p_inv_econ_shrunk', 'p_wpa_shrunk', 'p_rse_shrunk', 'p_dot_shrunk', 'delta_rse', 'p_pos_rate']:
        bowl_eligible[f'z_{col}'] = stats.zscore(bowl_eligible[col].fillna(0))

    # Official 5-Component Bowler Scoring Formula (Strictly Preserved)
    bowl_eligible['bowler_score'] = (
        0.30 * bowl_eligible['z_p_inv_econ_shrunk'] +
        0.25 * bowl_eligible['z_p_wpa_shrunk']      +
        0.20 * bowl_eligible['z_p_dot_shrunk']      +
        0.15 * bowl_eligible['z_delta_rse']        +
        0.10 * bowl_eligible['z_p_pos_rate']
    )

    bowl_eligible['final_rank'] = bowl_eligible['bowler_score'].rank(ascending=False).astype(int)

    print(f"Eligible Pressure Bowlers (>= 250 balls): {len(bowl_eligible)}")
    display(bowl_eligible.sort_values('final_rank').head(10)[
        ['final_rank', 'player_name', 'p_balls', 'p_econ', 'p_dot_pct', 'p_wpa_ov', 'p_rse_ov', 'delta_rse', 'is_provisional', 'bowler_score']
    ])


    ctx.update({k: v for k, v in locals().items() if k in ['bowl_stats', 'bowl_eligible']})
    return ctx
