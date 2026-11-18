"""Data ingestion, competition scope filter and ball-by-ball cricket accounting."""
from .common import *


def run(ctx):
    DATA_DIR = ctx['DATA_DIR']
    expected = ['competitions.csv', 'matches.csv', 'teams.csv', 'playing_eleven.csv', 'ball_by_ball.csv']
    missing = [f for f in expected if not os.path.exists(os.path.join(DATA_DIR, f))]
    assert not missing, f'Missing data files in {os.path.abspath(DATA_DIR)}: {missing}'

    # CELL 3 — Multi-Table Data Ingestion
    competitions    = pd.read_csv(f"{DATA_DIR}/competitions.csv")
    matches         = pd.read_csv(f"{DATA_DIR}/matches.csv")
    teams           = pd.read_csv(f"{DATA_DIR}/teams.csv")
    playing_eleven  = pd.read_csv(f"{DATA_DIR}/playing_eleven.csv")
    comp_player_map = pd.read_csv(f"{DATA_DIR}/competition_team_player_mapping.csv")
    balls_raw       = pd.read_csv(f"{DATA_DIR}/ball_by_ball.csv", low_memory=False)

    print(f"Raw Competitions : {competitions.shape}")
    print(f"Raw Matches      : {matches.shape}")
    print(f"Raw Deliveries   : {balls_raw.shape}")
    assert len(balls_raw) > 100000, "ball_by_ball.csv incomplete"


    # CELL 4 — Strict Competition Scope & Quality Filtering (Jan 2022+)

    # 1. Scope: T20I and IPL
    competitions['format_clean'] = competitions['match_format'].astype(str).str.strip().str.upper()
    competitions['comp_name_lc'] = competitions['comp_name'].astype(str).str.strip().str.lower()

    t20i_comps = competitions[competitions['format_clean'] == 'T20I'].copy()
    ipl_comps  = competitions[
        (competitions['format_clean'] == 'T20') &
        (competitions['comp_name_lc'].str.contains('ipl|indian premier', na=False))
    ].copy()

    eligible_comps = pd.concat([ipl_comps, t20i_comps], ignore_index=True).drop_duplicates('comp_id')
    eligible_comp_ids = set(eligible_comps['comp_id'])

    # 2. Filter matches (from 2022-01-01, valid completed matches only)
    matches['match_date'] = pd.to_datetime(matches['match_date'], errors='coerce')

    # Drop abandoned/no-result matches where winner cannot be determined
    valid_matches = matches[
        (matches['comp_id'].isin(eligible_comp_ids)) &
        (matches['match_date'] >= '2022-01-01') &
        (matches['win_team_id'].notna()) &
        (matches['win_team_id'] != 0) &
        (~matches['result'].astype(str).str.lower().isin(['no result', 'abandoned']))
    ].copy()

    # Bring match_format and comp_name from competitions into valid_matches
    valid_matches = valid_matches.merge(
        eligible_comps[['comp_id', 'match_format', 'comp_name', 'season']],
        on='comp_id',
        how='left'
    )

    # Quality Filter: Keep IPL + Full-Member T20I to eliminate weak-opposition distortions
    FULL_MEMBERS = {
        'India', 'Australia', 'England', 'Pakistan', 'South Africa',
        'New Zealand', 'West Indies', 'Sri Lanka', 'Bangladesh',
        'Zimbabwe', 'Afghanistan', 'Ireland'
    }
    home_full = valid_matches['home_team'].isin(FULL_MEMBERS)
    away_full = valid_matches['away_team'].isin(FULL_MEMBERS)
    valid_matches['is_full_member_t20i'] = (home_full & away_full).astype(int)

    # Filter: All IPL matches + T20Is between full members
    eligible_matches = valid_matches[
        (valid_matches['match_format'].astype(str).str.upper() == 'T20') |
        (valid_matches['is_full_member_t20i'] == 1)
    ].copy()

    # Add context flags
    eligible_matches['is_ipl'] = (eligible_matches['match_format'].astype(str).str.upper() == 'T20').astype(int)
    eligible_matches['is_knockout'] = (
        eligible_matches['stage'].astype(str).str.lower().str.contains('final|semi|playoff|eliminator|qualifier', na=False) |
        (eligible_matches['knock_out'].fillna(0).astype(int) == 1)
    ).astype(int)

    eligible_match_ids = set(eligible_matches['match_id'])

    print(f"Eligible Competitions: {len(eligible_comps)}")
    print(f"Eligible Matches: {len(eligible_matches)} (IPL: {eligible_matches['is_ipl'].sum()}, Full-Member T20I: {(~eligible_matches['is_ipl'].astype(bool)).sum()})")
    assert len(eligible_matches) > 500, "Unexpectedly low number of eligible matches"


    # CELL 5 — Rigorous Cricket Delivery Accounting & Dismissal Attribution

    # 1. Filter deliveries to eligible matches and normal innings (1 and 2 only, no super overs)
    balls = balls_raw[
        (balls_raw['match_id'].isin(eligible_match_ids)) &
        (balls_raw['innings'].isin([1, 2]))
    ].copy()

    # 2. Strict Delivery Legality
    balls['extras_type_clean'] = balls['extras_type'].astype(str).str.strip().str.lower()
    balls['is_wide']   = (balls['extras_type_clean'] == 'wide').astype(int)
    balls['is_noball'] = (balls['extras_type_clean'].isin(['overstep', 'no ball', 'noball'])).astype(int)
    balls['is_legal']  = (1 - balls['is_wide'] - balls['is_noball']).clip(0, 1)

    # Balls faced by batter under official MCC laws: no-balls count as balls faced, wides DO NOT count as balls faced!
    balls['is_ball_faced'] = (balls['is_wide'] == 0).astype(int)

    # 3. Cricket Accounting: Batter runs vs Bowler runs vs Team runs
    balls['bat_runs'] = pd.to_numeric(balls['runs'], errors='coerce').fillna(0).astype(int)
    balls['extras1_runs_num'] = pd.to_numeric(balls['extras1_runs'], errors='coerce').fillna(0).astype(int)
    balls['extras_2_runs_num'] = pd.to_numeric(balls['extras_2_runs'], errors='coerce').fillna(0).astype(int)

    # Bowler extras: wides & noballs charged to bowler; byes & legbyes NOT charged to bowler
    balls['bowler_extras'] = np.where(
        balls['is_wide'] == 1,
        balls['extras1_runs_num'] + balls['extras_2_runs_num'],
        np.where(balls['is_noball'] == 1, balls['extras1_runs_num'] + balls['extras_2_runs_num'], 0)
    )
    balls['bowler_runs'] = balls['bat_runs'] + balls['bowler_extras']

    # Total team runs on delivery (bat runs + all extras)
    balls['team_runs'] = balls['bat_runs'] + balls['extras1_runs_num'] + balls['extras_2_runs_num']

    # Dot ball accounting (Requirement 5):
    # A true dot ball is a LEGAL ball where NO team runs are scored (neither bat runs nor byes/leg-byes).
    balls['is_dot'] = ((balls['is_legal'] == 1) & (balls['team_runs'] == 0)).astype(int)

    # 4. Strict Dismissal Accounting & Individual Attribution (Requirement 4 & 6):
    balls['is_wicket_flag'] = balls['is_wicket'].astype(str).str.strip().str.lower().isin(['true', '1'])
    balls['dismissal_type_clean'] = balls['dismissal_type'].astype(str).str.strip()

    non_bowler_dismissals = ['RunOut', 'Retire Out', 'Obstracting the field', 'Obstructing the field', 'None', '']
    balls['is_bowler_wicket'] = (
        balls['is_wicket_flag'] &
        (~balls['dismissal_type_clean'].isin(non_bowler_dismissals))
    ).astype(int)

    # Distinguish striker dismissal vs non-striker dismissal using dismissed_player_id
    balls['dismissed_player_id_clean'] = pd.to_numeric(balls['dismissed_player_id'], errors='coerce').fillna(0).astype(int)
    balls['striker_id'] = pd.to_numeric(balls['striker_id'], errors='coerce').fillna(0).astype(int)
    balls['non_striker_id'] = pd.to_numeric(balls['non_striker_id'], errors='coerce').fillna(0).astype(int)
    balls['bowler_id'] = pd.to_numeric(balls['bowler_id'], errors='coerce').fillna(0).astype(int)

    # Striker is out only if the dismissed player is the striker, OR if dismissed_player_id is unrecorded on a non-runout
    balls['is_striker_out'] = (
        balls['is_wicket_flag'] &
        ((balls['dismissed_player_id_clean'] == balls['striker_id']) | 
         ((balls['dismissed_player_id_clean'] == 0) & (balls['dismissal_type_clean'] != 'RunOut')))
    ).astype(int)

    # Non-striker was out (e.g. non-striker run-out) — striker must NOT be charged!
    balls['is_non_striker_out'] = (
        balls['is_wicket_flag'] &
        (balls['dismissed_player_id_clean'] == balls['non_striker_id'])
    ).astype(int)

    balls['is_batter_out'] = balls['is_striker_out']  # Batter personal stat reflects their own dismissal

    # 5. Canonical Player Mapping
    player_name_map = {}
    for _, row in balls[['striker_id', 'striker_name']].drop_duplicates().iterrows():
        if row['striker_id'] != 0 and pd.notna(row['striker_name']):
            player_name_map[int(row['striker_id'])] = str(row['striker_name']).strip()
    for _, row in balls[['bowler_id', 'bowler_name']].drop_duplicates().iterrows():
        if row['bowler_id'] != 0 and pd.notna(row['bowler_name']):
            player_name_map[int(row['bowler_id'])] = str(row['bowler_name']).strip()
    for _, row in balls[['non_striker_id', 'non_striker_name']].drop_duplicates().iterrows():
        if row['non_striker_id'] != 0 and pd.notna(row['non_striker_name']):
            player_name_map[int(row['non_striker_id'])] = str(row['non_striker_name']).strip()

    # Sort strictly chronologically
    balls = balls.sort_values(['match_id', 'innings', 'overid', 'over_ball_num']).reset_index(drop=True)

    # Reconciliation assertions (Requirement 6)
    raw_eligible_runs = pd.to_numeric(balls_raw[balls_raw['match_id'].isin(eligible_match_ids) & balls_raw['innings'].isin([1, 2])]['runs'], errors='coerce').fillna(0).sum()
    assert balls['bat_runs'].sum() == raw_eligible_runs, "Bat runs mismatch against raw data"
    print(f"Sanitized Deliveries: {len(balls):,}")
    print(f"Total Legal Balls: {balls['is_legal'].sum():,} | Balls Faced: {balls['is_ball_faced'].sum():,} | True Dots: {balls['is_dot'].sum():,}")
    print(f"Striker Outs: {balls['is_striker_out'].sum():,} | Non-Striker Outs: {balls['is_non_striker_out'].sum():,} | Bowler Wickets: {balls['is_bowler_wicket'].sum():,}")


    ctx.update({k: v for k, v in locals().items() if k in ['competitions', 'matches', 'teams', 'playing_eleven', 'comp_player_map', 'balls_raw', 'eligible_matches', 'eligible_match_ids', 'balls', 'player_name_map']})
    return ctx
