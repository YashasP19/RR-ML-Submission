"""Quadrant and rank-interval plots."""
from .common import *


def run(ctx):
    bat_eligible = ctx['bat_eligible']
    bowl_eligible = ctx['bowl_eligible']
    OUT_DIR = ctx['OUT_DIR']

    # CELL 13 — Visualizations: Two-Axis Quadrants & Rank Interval Forest Plots

    fig, axes = plt.subplots(2, 2, figsize=(16, 13))

    # 1. Batter Performance Quadrant (WPA vs Elevation Delta)
    ax = axes[0, 0]
    top10_b = bat_eligible.sort_values('final_rank').head(10)
    ax.scatter(bat_eligible['delta_rae'], bat_eligible['p_wpa100'], color='lightgray', alpha=0.6, label='Eligible Pool')
    ax.scatter(top10_b['delta_rae'], top10_b['p_wpa100'], color='crimson', s=90, zorder=5, label='Top 10 Batters')
    for _, r in top10_b.iterrows():
        ax.annotate(r['player_name'], (r['delta_rae'], r['p_wpa100']), fontsize=9, xytext=(5, 2), textcoords='offset points')
    ax.axvline(0, color='gray', linestyle='--', alpha=0.7)
    ax.axhline(0, color='gray', linestyle='--', alpha=0.7)
    ax.set_xlabel('Pressure Elevation Delta (RAE/100 diff vs Normal)')
    ax.set_ylabel('Absolute Pressure WPA / 100 Balls')
    ax.set_title('Batter Impact Quadrant: Absolute vs Elevation Under Pressure')
    ax.legend(loc='lower right')

    # 2. Bowler Performance Quadrant (Economy vs Baseline Suppression Delta)
    ax = axes[0, 1]
    top10_bw = bowl_eligible.sort_values('final_rank').head(10)
    ax.scatter(bowl_eligible['delta_rse'], bowl_eligible['p_econ'], color='lightgray', alpha=0.6, label='Eligible Pool')
    ax.scatter(top10_bw['delta_rse'], top10_bw['p_econ'], color='darkblue', s=90, zorder=5, label='Top 10 Bowlers')
    for _, r in top10_bw.iterrows():
        ax.annotate(r['player_name'], (r['delta_rse'], r['p_econ']), fontsize=9, xytext=(5, 2), textcoords='offset points')
    ax.axvline(0, color='gray', linestyle='--', alpha=0.7)
    ax.invert_yaxis()  # Lower economy is better
    ax.set_xlabel('RSE/over Elevation Under Pressure (Pressure - Normal)')
    ax.set_ylabel('Pressure Economy Rate (Inverted: Lower is Better)')
    ax.set_title('Bowler Impact Quadrant: Suppression vs Elevation Under Pressure')
    ax.legend(loc='lower left')

    # 3. Batter Rank Forest Plot (10th to 90th percentile intervals)
    ax = axes[1, 0]
    top10_b_f = top10_b.reset_index(drop=True)
    y_b = range(len(top10_b_f))
    ax.barh(y_b, top10_b_f['boot_p90'] - top10_b_f['boot_p10'], left=top10_b_f['boot_p10'], color='cornflowerblue', alpha=0.55)
    ax.scatter(top10_b_f['boot_median'], y_b, color='navy', zorder=5)
    ax.set_yticks(list(y_b))
    ax.set_yticklabels(top10_b_f['player_name'], fontsize=9)
    ax.invert_xaxis()
    ax.set_xlabel('Bootstrap Rank Interval (Lower = Better)')
    ax.set_title('Batter Rank Stability (10th–90th Percentile Intervals)')

    # 4. Bowler Rank Forest Plot
    ax = axes[1, 1]
    top10_bw_f = top10_bw.reset_index(drop=True)
    y_bw = range(len(top10_bw_f))
    ax.barh(y_bw, top10_bw_f['boot_p90'] - top10_bw_f['boot_p10'], left=top10_bw_f['boot_p10'], color='lightgreen', alpha=0.55)
    ax.scatter(top10_bw_f['boot_median'], y_bw, color='darkgreen', zorder=5)
    ax.set_yticks(list(y_bw))
    ax.set_yticklabels(top10_bw_f['player_name'], fontsize=9)
    ax.invert_xaxis()
    ax.set_xlabel('Bootstrap Rank Interval (Lower = Better)')
    ax.set_title('Bowler Rank Stability (10th–90th Percentile Intervals)')

    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'pressure_analysis_v3.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("Visualization suite executed and saved to pressure_analysis_v3.png.")


    ctx.update({k: v for k, v in locals().items() if k in []})
    return ctx
