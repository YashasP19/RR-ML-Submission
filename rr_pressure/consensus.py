"""Consensus final ranking (baseline + bootstrap + eligibility variants) and submission CSVs."""
from .common import *


def run(ctx):
    bat_eligible = ctx['bat_eligible']
    bowl_eligible = ctx['bowl_eligible']
    bat_stats = ctx['bat_stats']
    bowl_stats = ctx['bowl_stats']
    _rank_batters_at = ctx['_rank_batters_at']
    _rank_bowlers_at = ctx['_rank_bowlers_at']
    OUT_DIR = ctx['OUT_DIR']

    # CELL 16 — CONSENSUS FINAL RANKING (baseline + bootstrap median + eligibility-cutoff variants)
    ELIG_FLOOR_TOP3 = 0.75   # podium (ranks 1-3)
    ELIG_FLOOR_TOP10 = 0.70  # everyone else in the top 10

    def consensus_table(elig, stats_all, id_col, rank_fn, cuts, base_cut, label):
        n = len(elig)
        t = elig[[id_col, 'player_name', 'final_rank', 'boot_median', 'p_elig', 'p_balls']].copy()
        t['pct_base'] = t['final_rank'] / n
        t['pct_boot'] = t['boot_median'].fillna(n) / n
        var = []
        for cut in cuts:
            if cut == base_cut: continue
            d = rank_fn(cut)
            var.append(pd.Series((d['rank'] / len(d)).values, index=d[id_col].values))
        if var:
            cutdf = pd.concat(var, axis=1)
            t['pct_cut'] = t[id_col].map(cutdf.mean(axis=1))
        else:
            t['pct_cut'] = np.nan
        t['pct_cut'] = t['pct_cut'].fillna(t['pct_base'])
        t['consensus'] = (t['pct_base'] + t['pct_boot'] + t['pct_cut']) / 3.0
        t = t.sort_values('consensus').reset_index(drop=True)
        # P(eligible) floor for the podium: ineligible-risk players cannot take ranks 1-3
        # Eligibility floors: podium needs >= 75%, the rest of the top 10 needs >= 70%.
        podium = t[t['p_elig'] >= ELIG_FLOOR_TOP3].head(3)
        others = t[(t['p_elig'] >= ELIG_FLOOR_TOP10) & ~t.index.isin(podium.index)].head(7)
        rest = t[~t.index.isin(podium.index) & ~t.index.isin(others.index)]
        final = pd.concat([podium, others, rest]).reset_index(drop=True)
        final['Rank'] = np.arange(1, len(final) + 1)
        return final

    bat_cons  = consensus_table(bat_eligible,  bat_stats,  'striker_id', _rank_batters_at, [100, 150, 200, 250], 150, 'batters')
    bowl_cons = consensus_table(bowl_eligible, bowl_stats, 'bowler_id',  _rank_bowlers_at, [150, 200, 250, 300], 250, 'bowlers')

    cols = ['Rank', 'player_name', 'final_rank', 'boot_median', 'p_elig', 'p_balls', 'consensus']
    print("=" * 80); print("FINAL SUBMISSION - TOP 10 BATTERS (consensus)"); print("=" * 80)
    display(bat_cons.head(10)[cols])
    print("\nNext 10 batters (for context):"); display(bat_cons.iloc[10:20][cols])
    print("=" * 80); print("FINAL SUBMISSION - TOP 10 BOWLERS (consensus)"); print("=" * 80)
    display(bowl_cons.head(10)[cols])
    print("\nNext 10 bowlers (for context):"); display(bowl_cons.iloc[10:20][cols])

    def where_is(names, cons, stats_all, count_col='p_balls'):
        for nm in names:
            hit = cons[cons['player_name'].astype(str).str.contains(nm, case=False, na=False)]
            if len(hit):
                r = hit.iloc[0]; print(f"  {r['player_name']:<22} consensus rank {int(r['Rank']):>2} / {len(cons)} (baseline {int(r['final_rank'])}, P(elig) {r['p_elig']:.0%})")
            else:
                h2 = stats_all[stats_all['player_name'].astype(str).str.contains(nm, case=False, na=False)]
                if len(h2): print(f"  {h2.iloc[0]['player_name']:<22} NOT ELIGIBLE (pressure balls = {int(h2.iloc[0][count_col])})")
                else: print(f"  {nm:<22} not found in scope")
    print("\nSpot-check - notable batters:")
    where_is(['Abhishek Sharma', 'Pooran', 'Buttler', 'Suryakumar', 'Kohli', 'Rinku', 'Samson'], bat_cons, bat_stats)
    print("Spot-check - notable bowlers:")
    where_is(['Bumrah', 'Rashid Khan', 'Arshdeep', 'Pathirana', 'Narine', 'Chakravarthy', 'Siraj'], bowl_cons, bowl_stats)

    assert bat_cons.head(10)['player_name'].nunique() == 10 and bowl_cons.head(10)['player_name'].nunique() == 10
    bat_cons.head(10)[cols].to_csv(os.path.join(OUT_DIR, 'top10_batters_consensus.csv'), index=False)
    bowl_cons.head(10)[cols].to_csv(os.path.join(OUT_DIR, 'top10_bowlers_consensus.csv'), index=False)
    print("\nExported top10_batters_consensus.csv and top10_bowlers_consensus.csv - SUBMIT THESE.")



    # ---- full player tables for the web app (one row per eligible player, consensus rank included)
    _b = bat_eligible.merge(bat_cons[['striker_id', 'Rank', 'consensus']], on='striker_id')
    _b[['striker_id', 'player_name', 'Rank', 'consensus', 'final_rank', 'boot_median', 'p_elig', 'p_top10_uncond',
        'p_balls', 'p_sr', 'p_wpa100', 'p_rae100', 'delta_rae', 'p_pos_rate']].sort_values('Rank').to_csv(
        os.path.join(OUT_DIR, 'players_batters.csv'), index=False)
    _w = bowl_eligible.merge(bowl_cons[['bowler_id', 'Rank', 'consensus']], on='bowler_id')
    _w[['bowler_id', 'player_name', 'Rank', 'consensus', 'final_rank', 'boot_median', 'p_elig', 'p_top10_uncond',
        'p_balls', 'p_econ', 'p_dot_pct', 'p_wpa_ov', 'p_rse_ov', 'delta_rse', 'p_pos_rate']].sort_values('Rank').to_csv(
        os.path.join(OUT_DIR, 'players_bowlers.csv'), index=False)
    print("Exported players_batters.csv and players_bowlers.csv")

    ctx.update({k: v for k, v in locals().items() if k in []})
    return ctx
