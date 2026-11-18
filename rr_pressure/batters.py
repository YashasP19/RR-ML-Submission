"""Batter pressure metrics, Empirical Bayes shrinkage, elevation and composite score."""
from .common import *


def run(ctx):
    balls = ctx['balls']
    player_name_map = ctx['player_name_map']

    # CELL 10 — Batter Metrics: Absolute Pressure Impact & Baseline Delta
    # Requirement 6 & 9: Proper balls faced (no-balls count, wides do not), adaptive EB, provisional tags

    # Use balls faced for batting aggregation (balls_faced count includes legal + no-balls, excludes wides)
    faced_balls = balls[balls['is_ball_faced'] == 1].copy()

    def aggregate_batter_stats(df, label):
        agg_df = df.groupby('striker_id').agg(
            balls=('is_ball_faced', 'sum'),
            runs=('bat_runs', 'sum'),
            dismissals=('is_striker_out', 'sum'),
            total_wpa=('batter_wpa', 'sum'),
            total_rae=('batter_rae', 'sum'),
            dots=('bat_runs', lambda x: np.sum(x == 0)),
            boundaries=('bat_runs', lambda x: np.sum(x.isin([4, 5, 6])))
        ).reset_index()
    
        agg_df[f'{label}_balls']   = agg_df['balls']
        agg_df[f'{label}_sr']      = 100.0 * agg_df['runs'] / agg_df['balls'].replace(0, np.nan)
        agg_df[f'{label}_wpa100']  = 100.0 * agg_df['total_wpa'] / agg_df['balls'].replace(0, np.nan)
        agg_df[f'{label}_rae100']  = 100.0 * agg_df['total_rae'] / agg_df['balls'].replace(0, np.nan)
        agg_df[f'{label}_dot_pct'] = 100.0 * agg_df['dots'] / agg_df['balls'].replace(0, np.nan)
        agg_df[f'{label}_avg']     = agg_df['runs'] / agg_df['dismissals'].replace(0, np.nan)
    
        # Consistency: % of pressure innings (with >= 5 balls faced) having positive net WPA
        inn_wpa = df.groupby(['striker_id', 'match_id', 'innings']).agg(
            wpa_sum=('batter_wpa', 'sum'),
            balls_count=('is_ball_faced', 'sum')
        ).reset_index()
        inn_qual = inn_wpa[inn_wpa['balls_count'] >= 5]
        inn_stats = inn_qual.groupby('striker_id').agg(
            pos_wpa_rate=('wpa_sum', lambda x: np.mean(x > 0)),
            wpa_sd=('wpa_sum', 'std'),
            n_inn=('wpa_sum', 'size'),
            n_pos=('wpa_sum', lambda x: int(np.sum(x > 0)))
        ).reset_index()
        agg_df[f'{label}_n_inn'] = agg_df['striker_id'].map(inn_stats.set_index('striker_id')['n_inn']).fillna(0)
        agg_df[f'{label}_n_pos'] = agg_df['striker_id'].map(inn_stats.set_index('striker_id')['n_pos']).fillna(0)
        agg_df[f'{label}_pos_rate'] = agg_df['striker_id'].map(inn_stats.set_index('striker_id')['pos_wpa_rate']).fillna(0)
    
        return agg_df[['striker_id', f'{label}_balls', f'{label}_sr', f'{label}_wpa100', f'{label}_rae100', f'{label}_dot_pct', f'{label}_avg', f'{label}_pos_rate', f'{label}_n_inn', f'{label}_n_pos']]

    p_bat = aggregate_batter_stats(faced_balls[faced_balls['is_pressure'] == 1], 'p')
    n_bat = aggregate_batter_stats(faced_balls[faced_balls['is_pressure'] == 0], 'n')

    bat_stats = p_bat.merge(n_bat, on='striker_id', how='left')
    bat_stats['player_name'] = bat_stats['striker_id'].map(player_name_map)

    # Official Eligibility: >= 150 pressure balls faced
    bat_eligible = bat_stats[bat_stats['p_balls'] >= 150].copy()

    # Provisional Tagging (Requirement 9: Flag players within 15% of eligibility threshold)
    bat_eligible['is_provisional'] = np.where(bat_eligible['p_balls'] < 175, 'Provisional (Near Cutoff)', 'Established')

    bat_eligible['p_wpa_shrunk'] = eb_shrink_adaptive(bat_eligible['p_wpa100'], bat_eligible['p_balls'], 120, 350)
    bat_eligible['p_rae_shrunk'] = eb_shrink_adaptive(bat_eligible['p_rae100'], bat_eligible['p_balls'], 120, 350)
    bat_eligible['p_sr_shrunk']  = eb_shrink_adaptive(bat_eligible['p_sr'], bat_eligible['p_balls'], 120, 350)

    # Baseline Delta (Elevation under pressure vs normal)
    # FIX 4: elevation uses RAE (already context-adjusted) - WPA/100 on normal balls is ~0 by construction
    bat_eligible['n_rae_shrunk'] = eb_shrink_adaptive(bat_eligible['n_rae100'].fillna(bat_eligible['n_rae100'].mean()), bat_eligible['n_balls'].fillna(0), 120, 350)
    bat_eligible['delta_rae']    = bat_eligible['p_rae_shrunk'] - bat_eligible['n_rae_shrunk']

    # FIX 6: consistency rate shrunk toward pooled rate (raw rate kept for reference)
    bat_eligible['p_pos_rate_raw'] = bat_eligible['p_pos_rate']
    bat_eligible['p_pos_rate'] = eb_shrink_rate(bat_eligible['p_n_pos'], bat_eligible['p_n_inn']).values

    # Standardize with Z-scores
    for col in ['p_wpa_shrunk', 'p_rae_shrunk', 'p_sr_shrunk', 'delta_rae', 'p_pos_rate']:
        bat_eligible[f'z_{col}'] = stats.zscore(bat_eligible[col].fillna(0))

    # Official 5-Component Batter Scoring Formula (Strictly Preserved)
    bat_eligible['batter_score'] = (
        0.35 * bat_eligible['z_p_wpa_shrunk'] +
        0.25 * bat_eligible['z_p_rae_shrunk'] +
        0.20 * bat_eligible['z_delta_rae']    +
        0.10 * bat_eligible['z_p_sr_shrunk']  +
        0.10 * bat_eligible['z_p_pos_rate']
    )

    bat_eligible['final_rank'] = bat_eligible['batter_score'].rank(ascending=False).astype(int)

    print(f"Eligible Pressure Batters (>= 150 balls): {len(bat_eligible)}")
    display(bat_eligible.sort_values('final_rank').head(10)[
        ['final_rank', 'player_name', 'p_balls', 'p_sr', 'p_wpa100', 'p_rae100', 'delta_rae', 'p_pos_rate', 'is_provisional', 'batter_score']
    ])


    ctx.update({k: v for k, v in locals().items() if k in ['faced_balls', 'bat_stats', 'bat_eligible', 'p_bat', 'n_bat']})
    return ctx
