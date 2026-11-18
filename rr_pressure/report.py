"""Baseline top-10 tables and CSV export."""
from .common import *


def run(ctx):
    bat_eligible = ctx['bat_eligible']
    bowl_eligible = ctx['bowl_eligible']
    OUT_DIR = ctx['OUT_DIR']

    # CELL 14 — Final Official Top-10 Submission Tables & CSV Export
    # Requirement 10 & 11: Export final Top-10 tables (CSV) with provisional status, unconditional and conditional P(Top 10)

    print("=" * 80)
    print("TOP 10 BATTERS UNDER PRESSURE (SupeRR Selector Season 2)")
    print("=" * 80)

    final_batters = bat_eligible.sort_values('final_rank').head(10)[[
        'final_rank', 'player_name', 'p_balls', 'p_sr', 'p_wpa100', 'p_rae100', 'delta_rae', 'p_elig', 'p_top10_uncond', 'p_top10_cond', 'is_provisional'
    ]].rename(columns={
        'final_rank': 'Rank',
        'player_name': 'Player',
        'p_balls': 'Pressure Balls',
        'p_sr': 'Pressure SR',
        'p_wpa100': 'WPA / 100 Balls',
        'p_rae100': 'RAE / 100 Balls',
        'delta_rae': 'Elevation Δ',
        'p_elig': 'P(Eligible)',
        'p_top10_uncond': 'P(Top 10 Unconditional)',
        'p_top10_cond': 'P(Top 10 | Eligible)',
        'is_provisional': 'Status'
    })

    final_batters['P(Eligible)'] = final_batters['P(Eligible)'].map('{:.0%}'.format)
    final_batters['P(Top 10 Unconditional)'] = final_batters['P(Top 10 Unconditional)'].map('{:.0%}'.format)
    final_batters['P(Top 10 | Eligible)'] = final_batters['P(Top 10 | Eligible)'].map('{:.0%}'.format)
    final_batters['Pressure SR'] = final_batters['Pressure SR'].map('{:.1f}'.format)
    final_batters['WPA / 100 Balls'] = final_batters['WPA / 100 Balls'].map('{:.2f}'.format)
    final_batters['RAE / 100 Balls'] = final_batters['RAE / 100 Balls'].map('{:.2f}'.format)
    final_batters['Elevation Δ'] = final_batters['Elevation Δ'].map('{:.2f}'.format)

    display(final_batters)
    final_batters.to_csv(os.path.join(OUT_DIR, 'top10_batters_official.csv'), index=False)
    print("Exported top10_batters_official.csv successfully.")

    print("\n" + "=" * 80)
    print("TOP 10 BOWLERS UNDER PRESSURE (SupeRR Selector Season 2)")
    print("=" * 80)

    final_bowlers = bowl_eligible.sort_values('final_rank').head(10)[[
        'final_rank', 'player_name', 'p_balls', 'p_econ', 'p_dot_pct', 'p_wpa_ov', 'delta_rse', 'p_elig', 'p_top10_uncond', 'p_top10_cond', 'is_provisional'
    ]].rename(columns={
        'final_rank': 'Rank',
        'player_name': 'Player',
        'p_balls': 'Pressure Balls',
        'p_econ': 'Pressure Econ',
        'p_dot_pct': 'True Dot %',
        'p_wpa_ov': 'WPA / Over',
        'delta_rse': 'RSE Elevation Δ',
        'p_elig': 'P(Eligible)',
        'p_top10_uncond': 'P(Top 10 Unconditional)',
        'p_top10_cond': 'P(Top 10 | Eligible)',
        'is_provisional': 'Status'
    })

    final_bowlers['P(Eligible)'] = final_bowlers['P(Eligible)'].map('{:.0%}'.format)
    final_bowlers['P(Top 10 Unconditional)'] = final_bowlers['P(Top 10 Unconditional)'].map('{:.0%}'.format)
    final_bowlers['P(Top 10 | Eligible)'] = final_bowlers['P(Top 10 | Eligible)'].map('{:.0%}'.format)
    final_bowlers['Pressure Econ'] = final_bowlers['Pressure Econ'].map('{:.2f}'.format)
    final_bowlers['True Dot %'] = final_bowlers['True Dot %'].map('{:.1f}%'.format)
    final_bowlers['WPA / Over'] = final_bowlers['WPA / Over'].map('{:.3f}'.format)
    final_bowlers['RSE Elevation Δ'] = final_bowlers['RSE Elevation Δ'].map('{:+.2f}'.format)

    display(final_bowlers)
    final_bowlers.to_csv(os.path.join(OUT_DIR, 'top10_bowlers_official.csv'), index=False)
    print("Exported top10_bowlers_official.csv successfully.")

    # Requirement 10 assertions
    assert len(final_batters['Player'].unique()) == 10, "Duplicate batters in Top 10!"
    assert len(final_bowlers['Player'].unique()) == 10, "Duplicate bowlers in Top 10!"
    assert list(final_batters['Rank']) == list(range(1, 11)), "Non-monotonic batter ranks!"
    assert list(final_bowlers['Rank']) == list(range(1, 11)), "Non-monotonic bowler ranks!"


    ctx.update({k: v for k, v in locals().items() if k in ['final_batters', 'final_bowlers']})
    return ctx
