"""Innings state engine: cumulative score, wickets, balls remaining, target, required rate, venue par."""
from .common import *


def run(ctx):
    balls = ctx['balls']
    eligible_matches = ctx['eligible_matches']

    # CELL 6 — Innings State Engine (Cumulative Runs, Wickets, Targets, Balls Remaining, RRR)

    # 1. Merge match context
    match_cols = [
        'match_id', 'comp_id', 'match_date', 'venue_id', 'is_ipl', 'is_knockout',
        'win_team_id', 'home_team_id', 'away_team_id', 'revised_target',
        'first_inn_revised_overs', 'second_inn_revised_overs'
    ]
    balls = balls.merge(eligible_matches[match_cols], on='match_id', how='left')

    # 2. Cumulative Runs, Wickets, and Legal Balls within Innings
    balls['cum_team_runs'] = balls.groupby(['match_id', 'innings'])['team_runs'].transform(lambda x: x.shift(1).fillna(0).cumsum()).astype(int)
    balls['any_wicket']    = balls['is_wicket_flag'].astype(int)
    balls['cum_wickets']   = balls.groupby(['match_id', 'innings'])['any_wicket'].transform(lambda x: x.shift(1).fillna(0).cumsum()).astype(int)
    balls['cum_legal']     = balls.groupby(['match_id', 'innings'])['is_legal'].transform(lambda x: x.shift(1).fillna(0).cumsum()).astype(int)
    balls['wickets_in_hand'] = (10 - balls['cum_wickets']).clip(0, 10)

    # 3. Balls Remaining (accurately handling rain-reduced matches)
    def calc_total_balls(row):
        rev = row['first_inn_revised_overs'] if row['innings'] == 1 else row['second_inn_revised_overs']
        if pd.notna(rev) and float(rev) > 0:
            return int(float(rev) * 6)
        return 120

    balls['total_legal_balls'] = balls.apply(calc_total_balls, axis=1)
    balls['balls_remaining']   = (balls['total_legal_balls'] - balls['cum_legal']).clip(lower=0)

    # 4. Target Calculation for Innings 2 (prioritizing official revised_target)
    inn1_actual_totals = balls[balls['innings'] == 1].groupby('match_id')['team_runs'].sum().reset_index().rename(columns={'team_runs': 'inn1_actual_total'})
    balls = balls.merge(inn1_actual_totals, on='match_id', how='left')

    balls['target'] = np.where(
        balls['innings'] == 2,
        np.where(balls['revised_target'].notna() & (balls['revised_target'] > 0),
                 balls['revised_target'],
                 balls['inn1_actual_total'] + 1),
        np.nan
    )

    balls['runs_needed'] = np.where(
        balls['innings'] == 2,
        (balls['target'] - balls['cum_team_runs']).clip(lower=0),
        np.nan
    )

    balls['rrr'] = np.where(
        (balls['innings'] == 2) & (balls['balls_remaining'] > 0),
        balls['runs_needed'] / (balls['balls_remaining'] / 6.0),
        np.nan
    )

    # 5. Batting Team Won Target Variable (binary 0 or 1)
    balls['batting_team_won'] = (balls['batting_team_id'] == balls['win_team_id']).astype(int)

    # 6. Jackknife Leave-One-Match-Out Venue Par Score (Requirement 3: strictly zero leakage)
    venue_matches = balls[['venue_id', 'match_id', 'inn1_actual_total']].drop_duplicates()
    venue_sums    = venue_matches.groupby('venue_id')['inn1_actual_total'].transform('sum')
    venue_counts  = venue_matches.groupby('venue_id')['inn1_actual_total'].transform('count')
    venue_matches['venue_par_score'] = np.where(
        venue_counts > 1,
        (venue_sums - venue_matches['inn1_actual_total']) / (venue_counts - 1),
        165.0  # global T20 median par fallback
    )
    balls = balls.merge(venue_matches[['venue_id', 'match_id', 'venue_par_score']], on=['venue_id', 'match_id'], how='left')
    balls['venue_par_score'] = balls['venue_par_score'].fillna(165.0)

    print("Innings State Engine complete.")
    assert balls['batting_team_won'].isin([0, 1]).all(), "batting_team_won must be strictly binary"
    print(balls[['match_id', 'innings', 'overid', 'cum_team_runs', 'wickets_in_hand', 'balls_remaining', 'target', 'runs_needed', 'venue_par_score']].head())


    ctx.update({k: v for k, v in locals().items() if k in ['balls']})
    return ctx
