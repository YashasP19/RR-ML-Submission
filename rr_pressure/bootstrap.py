"""500-resample match-level cluster bootstrap of eligibility and rank."""
from .common import *


def run(ctx):
    balls = ctx['balls']
    eligible_matches = ctx['eligible_matches']
    bat_eligible = ctx['bat_eligible']
    bowl_eligible = ctx['bowl_eligible']

    # CELL 12 — Coherent Bootstrap Stability Testing (500 Match-Level Resamples)
    # Requirement 7: Cluster bootstrap by match_id reporting P(eligible), unconditional P(Top 10), conditional P(Top 10 | eligible), and rank percentiles

    N_BOOT = 500
    rng = np.random.default_rng(SEED)

    match_list = eligible_matches['match_id'].unique()
    n_matches  = len(match_list)

    # Pre-aggregate match-level contributions
    p_faced = balls[(balls['is_pressure'] == 1) & (balls['is_ball_faced'] == 1)].copy()
    n_faced = balls[(balls['is_pressure'] == 0) & (balls['is_ball_faced'] == 1)].copy()

    bat_p_match = p_faced.groupby(['match_id', 'striker_id']).agg(
        b=('is_ball_faced', 'sum'),
        r=('bat_runs', 'sum'),
        wpa=('batter_wpa', 'sum'),
        rae=('batter_rae', 'sum')
    ).reset_index()

    bat_n_match = n_faced.groupby(['match_id', 'striker_id']).agg(
        b_n=('is_ball_faced', 'sum'),
        r_n=('bat_runs', 'sum'),
        wpa_n=('batter_wpa', 'sum'),
        rae_n=('batter_rae', 'sum')
    ).reset_index()

    bat_p_inn = p_faced.groupby(['match_id', 'innings', 'striker_id']).agg(
        inn_b=('is_ball_faced', 'sum'),
        inn_wpa=('batter_wpa', 'sum')
    ).reset_index()
    bat_p_inn_qual = bat_p_inn[bat_p_inn['inn_b'] >= 5].copy()
    bat_p_inn_qual['pos_inn'] = (bat_p_inn_qual['inn_wpa'] > 0).astype(int)
    bat_p_inn_m = bat_p_inn_qual.groupby(['match_id', 'striker_id']).agg(
        n_qual_inns=('pos_inn', 'count'),
        n_pos_inns=('pos_inn', 'sum')
    ).reset_index()

    p_bowl_b = balls[balls['is_pressure'] == 1].copy()
    n_bowl_b = balls[balls['is_pressure'] == 0].copy()

    bowl_p_match = p_bowl_b.groupby(['match_id', 'bowler_id']).agg(
        b=('is_legal', 'sum'),
        rc=('bowler_runs', 'sum'),
        dots=('is_dot', 'sum'),
        wpa=('bowler_wpa', 'sum'),
        rse=('bowler_rse', 'sum')
    ).reset_index()

    bowl_n_match = n_bowl_b.groupby(['match_id', 'bowler_id']).agg(
        b_n=('is_legal', 'sum'),
        rc_n=('bowler_runs', 'sum'),
        rse_n=('bowler_rse', 'sum')
    ).reset_index()

    bowl_p_spell = p_bowl_b.groupby(['match_id', 'bowler_id']).agg(
        sp_b=('is_legal', 'sum'),
        sp_wpa=('bowler_wpa', 'sum')
    ).reset_index()
    bowl_p_spell_qual = bowl_p_spell[bowl_p_spell['sp_b'] >= 6].copy()
    bowl_p_spell_qual['pos_spell'] = (bowl_p_spell_qual['sp_wpa'] > 0).astype(int)
    bowl_p_spell_m = bowl_p_spell_qual.groupby(['match_id', 'bowler_id']).agg(
        n_qual_spells=('pos_spell', 'count'),
        n_pos_spells=('pos_spell', 'sum')
    ).reset_index()

    target_batters = bat_eligible['striker_id'].values
    target_bowlers = bowl_eligible['bowler_id'].values

    bat_boot_ranks  = {pid: [] for pid in target_batters}
    bat_boot_elig   = {pid: [] for pid in target_batters}

    bowl_boot_ranks = {pid: [] for pid in target_bowlers}
    bowl_boot_elig  = {pid: [] for pid in target_bowlers}

    print(f"Executing {N_BOOT} exact 5-component cluster bootstrap resamples...")

    for _ in range(N_BOOT):
        sampled_m = pd.Series(rng.choice(match_list, size=n_matches, replace=True)).value_counts()
        sample_w  = pd.DataFrame({'match_id': sampled_m.index, 'w': sampled_m.values})
    
        # 1. Batters
        bp = bat_p_match.merge(sample_w, on='match_id')
        bp['b_w'] = bp['b'] * bp['w']
        bp['r_w'] = bp['r'] * bp['w']
        bp['wpa_w'] = bp['wpa'] * bp['w']
        bp['rae_w'] = bp['rae'] * bp['w']
        bg = bp.groupby('striker_id').agg(b=('b_w', 'sum'), r=('r_w', 'sum'), wpa=('wpa_w', 'sum'), rae=('rae_w', 'sum'))
    
        for pid in target_batters:
            bat_boot_elig[pid].append(bool(bg.loc[pid, 'b'] >= 150) if pid in bg.index else False)
        
        bg = bg[bg['b'] >= 150].copy()
        if len(bg) > 5:
            bn = bat_n_match.merge(sample_w, on='match_id')
            bn['b_n_w'] = bn['b_n'] * bn['w']
            bn['rae_n_w'] = bn['rae_n'] * bn['w']
            bng = bn.groupby('striker_id').agg(b_n=('b_n_w', 'sum'), rae_n=('rae_n_w', 'sum'))
            bg = bg.join(bng, how='left')
        
            b_inn = bat_p_inn_m.merge(sample_w, on='match_id')
            b_inn['q_w'] = b_inn['n_qual_inns'] * b_inn['w']
            b_inn['p_w'] = b_inn['n_pos_inns'] * b_inn['w']
            b_inng = b_inn.groupby('striker_id').agg(tot_q=('q_w', 'sum'), tot_p=('p_w', 'sum'))
            bg = bg.join(b_inng, how='left')
        
            bg['p_sr']     = 100.0 * bg['r'] / bg['b']
            bg['p_wpa100'] = 100.0 * bg['wpa'] / bg['b']
            bg['p_rae100'] = 100.0 * bg['rae'] / bg['b']
            bg['n_rae100'] = 100.0 * bg['rae_n'] / bg['b_n'].replace(0, np.nan)
            bg['pos_rate'] = eb_shrink_rate(bg['tot_p'].fillna(0), bg['tot_q'].fillna(0)).values
        
            bg['p_wpa_shrunk'] = eb_shrink_adaptive(bg['p_wpa100'], bg['b'], 120, 350)
            bg['p_rae_shrunk'] = eb_shrink_adaptive(bg['p_rae100'], bg['b'], 120, 350)
            bg['p_sr_shrunk']  = eb_shrink_adaptive(bg['p_sr'], bg['b'], 120, 350)
            bg['n_rae_shrunk'] = eb_shrink_adaptive(bg['n_rae100'].fillna(bg['n_rae100'].mean()), bg['b_n'].fillna(0), 120, 350)
            bg['delta_rae']    = bg['p_rae_shrunk'] - bg['n_rae_shrunk']
        
            z_wpa   = stats.zscore(bg['p_wpa_shrunk'].fillna(0))
            z_rae   = stats.zscore(bg['p_rae_shrunk'].fillna(0))
            z_delta = stats.zscore(bg['delta_rae'].fillna(0))
            z_sr    = stats.zscore(bg['p_sr_shrunk'].fillna(0))
            z_pos   = stats.zscore(bg['pos_rate'].fillna(0))
        
            bg['score'] = 0.35 * z_wpa + 0.25 * z_rae + 0.20 * z_delta + 0.10 * z_sr + 0.10 * z_pos
            ranks_b = bg['score'].rank(ascending=False).to_dict()
            for pid in target_batters:
                bat_boot_ranks[pid].append(ranks_b.get(pid, np.nan))
        else:
            for pid in target_batters:
                bat_boot_ranks[pid].append(np.nan)
            
        # 2. Bowlers
        bwp = bowl_p_match.merge(sample_w, on='match_id')
        bwp['b_w']    = bwp['b']    * bwp['w']
        bwp['rc_w']   = bwp['rc']   * bwp['w']
        bwp['dots_w'] = bwp['dots'] * bwp['w']
        bwp['wpa_w']  = bwp['wpa']  * bwp['w']
        bwp['rse_w']  = bwp['rse']  * bwp['w']
        bwg = bwp.groupby('bowler_id').agg(b=('b_w', 'sum'), rc=('rc_w', 'sum'), dots=('dots_w', 'sum'), wpa=('wpa_w', 'sum'), rse=('rse_w', 'sum'))
    
        for pid in target_bowlers:
            bowl_boot_elig[pid].append(bool(bwg.loc[pid, 'b'] >= 250) if pid in bwg.index else False)
        
        bwg = bwg[bwg['b'] >= 250].copy()
        if len(bwg) > 5:
            bwn = bowl_n_match.merge(sample_w, on='match_id')
            bwn['b_n_w']  = bwn['b_n']  * bwn['w']
            bwn['rc_n_w'] = bwn['rc_n'] * bwn['w']
            bwn['rse_n_w'] = bwn['rse_n'] * bwn['w']
            bwng = bwn.groupby('bowler_id').agg(b_n=('b_n_w', 'sum'), rc_n=('rc_n_w', 'sum'), rse_n=('rse_n_w', 'sum'))
            bwg = bwg.join(bwng, how='left')
        
            bw_sp = bowl_p_spell_m.merge(sample_w, on='match_id')
            bw_sp['q_w'] = bw_sp['n_qual_spells'] * bw_sp['w']
            bw_sp['p_w'] = bw_sp['n_pos_spells'] * bw_sp['w']
            bw_spg = bw_sp.groupby('bowler_id').agg(tot_q=('q_w', 'sum'), tot_p=('p_w', 'sum'))
            bwg = bwg.join(bw_spg, how='left')
        
            bwg['p_econ']     = bwg['rc'] / (bwg['b'] / 6.0)
            bwg['p_inv_econ'] = 1.0 / bwg['p_econ'].replace(0, np.nan)
            bwg['p_dot_pct']  = 100.0 * bwg['dots'] / bwg['b']
            bwg['p_wpa_ov']   = bwg['wpa'] / (bwg['b'] / 6.0)
            bwg['p_rse_ov']   = bwg['rse'] / (bwg['b'] / 6.0)
            bwg['n_econ']     = bwg['rc_n'] / (bwg['b_n'].replace(0, np.nan) / 6.0)
            bwg['pos_rate']   = eb_shrink_rate(bwg['tot_p'].fillna(0), bwg['tot_q'].fillna(0)).values
        
            bwg['p_inv_econ_shrunk'] = eb_shrink_adaptive(bwg['p_inv_econ'], bwg['b'], 150, 450)
            bwg['p_wpa_shrunk']      = eb_shrink_adaptive(bwg['p_wpa_ov'], bwg['b'], 150, 450)
            bwg['p_dot_shrunk']      = eb_shrink_adaptive(bwg['p_dot_pct'], bwg['b'], 150, 450)
            bwg['n_rse_ov']          = bwg['rse_n'] / (bwg['b_n'].replace(0, np.nan) / 6.0)
            bwg['p_rse_shrunk']      = eb_shrink_adaptive(bwg['p_rse_ov'], bwg['b'], 150, 450)
            bwg['n_rse_shrunk']      = eb_shrink_adaptive(bwg['n_rse_ov'].fillna(bwg['n_rse_ov'].mean()), bwg['b_n'].fillna(0), 150, 450)
        
            bwg['delta_rse'] = bwg['p_rse_shrunk'] - bwg['n_rse_shrunk']
        
            z_econ  = stats.zscore(bwg['p_inv_econ_shrunk'].fillna(0))
            z_wpa   = stats.zscore(bwg['p_wpa_shrunk'].fillna(0))
            z_dot   = stats.zscore(bwg['p_dot_shrunk'].fillna(0))
            z_delta = stats.zscore(bwg['delta_rse'].fillna(0))
            z_pos   = stats.zscore(bwg['pos_rate'].fillna(0))
        
            bwg['score'] = 0.30 * z_econ + 0.25 * z_wpa + 0.20 * z_dot + 0.15 * z_delta + 0.10 * z_pos
            ranks_bw = bwg['score'].rank(ascending=False).to_dict()
            for pid in target_bowlers:
                bowl_boot_ranks[pid].append(ranks_bw.get(pid, np.nan))
        else:
            for pid in target_bowlers:
                bowl_boot_ranks[pid].append(np.nan)

    # Attach statistical intervals (Requirement 7)
    def calc_boot_stats(ranks_dict, elig_dict):
        p_elig, p_uncond, p_cond, med, p10, p90 = {}, {}, {}, {}, {}, {}
        for pid, r_list in ranks_dict.items():
            arr = np.array(r_list)
            e_arr = np.array(elig_dict[pid])
            p_elig[pid]   = np.mean(e_arr)
            p_uncond[pid] = np.mean(np.where(e_arr, arr <= 10, False))
            p_cond[pid]   = np.nanmean(arr[e_arr] <= 10) if np.sum(e_arr) > 0 else 0.0
            med[pid]      = np.nanmedian(arr) if np.sum(~np.isnan(arr)) > 0 else np.nan
            p10[pid]      = np.nanpercentile(arr, 10) if np.sum(~np.isnan(arr)) > 0 else np.nan
            p90[pid]      = np.nanpercentile(arr, 90) if np.sum(~np.isnan(arr)) > 0 else np.nan
        return p_elig, p_uncond, p_cond, med, p10, p90

    pe_b, pu_b, pc_b, med_b, p10_b, p90_b = calc_boot_stats(bat_boot_ranks, bat_boot_elig)
    bat_eligible['p_elig']         = bat_eligible['striker_id'].map(pe_b)
    bat_eligible['p_top10_uncond'] = bat_eligible['striker_id'].map(pu_b)
    bat_eligible['p_top10_cond']   = bat_eligible['striker_id'].map(pc_b)
    bat_eligible['boot_median']    = bat_eligible['striker_id'].map(med_b)
    bat_eligible['boot_p10']       = bat_eligible['striker_id'].map(p10_b)
    bat_eligible['boot_p90']       = bat_eligible['striker_id'].map(p90_b)

    pe_bw, pu_bw, pc_bw, med_bw, p10_bw, p90_bw = calc_boot_stats(bowl_boot_ranks, bowl_boot_elig)
    bowl_eligible['p_elig']         = bowl_eligible['bowler_id'].map(pe_bw)
    bowl_eligible['p_top10_uncond'] = bowl_eligible['bowler_id'].map(pu_bw)
    bowl_eligible['p_top10_cond']   = bowl_eligible['bowler_id'].map(pc_bw)
    bowl_eligible['boot_median']    = bowl_eligible['bowler_id'].map(med_bw)
    bowl_eligible['boot_p10']       = bowl_eligible['bowler_id'].map(p10_bw)
    bowl_eligible['boot_p90']       = bowl_eligible['bowler_id'].map(p90_bw)

    print("Exact 5-component Bootstrap Stability complete!")


    ctx.update({k: v for k, v in locals().items() if k in ['bat_eligible', 'bowl_eligible', 'p_bowl_b']})
    return ctx
