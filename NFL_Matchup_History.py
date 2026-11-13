"""Shared NFL divisional and head-to-head history features.

Optional data file: NFL_Historical_Games.csv
Required columns: Season, Week, Home_Team, Away_Team, Home_Score, Away_Score
"""

import os
import pandas as pd

HISTORICAL_GAMES_FILE = "NFL_Historical_Games.csv"
LOG_FILE = "NFL_Game_Log.csv"

TEAM_DIVISIONS = {
    "Bills": "AFC East", "Dolphins": "AFC East", "Patriots": "AFC East", "Jets": "AFC East",
    "Ravens": "AFC North", "Bengals": "AFC North", "Browns": "AFC North", "Steelers": "AFC North",
    "Texans": "AFC South", "Colts": "AFC South", "Jaguars": "AFC South", "Titans": "AFC South",
    "Broncos": "AFC West", "Chiefs": "AFC West", "Raiders": "AFC West", "Chargers": "AFC West",
    "Cowboys": "NFC East", "Giants": "NFC East", "Eagles": "NFC East", "Commanders": "NFC East",
    "Bears": "NFC North", "Lions": "NFC North", "Packers": "NFC North", "Vikings": "NFC North",
    "Falcons": "NFC South", "Panthers": "NFC South", "Saints": "NFC South", "Buccaneers": "NFC South",
    "Cardinals": "NFC West", "Rams": "NFC West", "49ers": "NFC West", "Seahawks": "NFC West",
}
TEAM_CONFERENCES = {team: division.split()[0] for team, division in TEAM_DIVISIONS.items()}
REQUIRED_COLUMNS = ["Season", "Week", "Home_Team", "Away_Team", "Home_Score", "Away_Score"]


def matchup_type_features(home_team, away_team):
    home_team = str(home_team).strip()
    away_team = str(away_team).strip()
    home_division = TEAM_DIVISIONS.get(home_team)
    away_division = TEAM_DIVISIONS.get(away_team)
    return {
        "same_division": int(home_division is not None and home_division == away_division),
        "same_conference": int(
            TEAM_CONFERENCES.get(home_team) is not None
            and TEAM_CONFERENCES.get(home_team) == TEAM_CONFERENCES.get(away_team)
        ),
    }


def load_matchup_games():
    """Load completed historical CSV games and completed prediction-log games."""
    frames = []

    if os.path.exists(HISTORICAL_GAMES_FILE):
        history = pd.read_csv(HISTORICAL_GAMES_FILE)
        missing = [column for column in REQUIRED_COLUMNS if column not in history.columns]
        if missing:
            raise ValueError(
                f"{HISTORICAL_GAMES_FILE} is missing columns: {', '.join(missing)}"
            )
        frames.append(history[REQUIRED_COLUMNS].copy())

    if os.path.exists(LOG_FILE):
        log = pd.read_csv(LOG_FILE)
        if {"Home_Team", "Away_Team", "Actual_Home_Score", "Actual_Away_Score"}.issubset(log.columns):
            if "Completed" in log.columns:
                log = log[log["Completed"].astype(str).str.lower().isin(["true", "1"])]
            log = log.copy()
            log["Season"] = pd.to_numeric(
                log.get("Prediction_Date", pd.Series(index=log.index, dtype=str)).astype(str).str[:4],
                errors="coerce",
            )
            # Game-log records do not normally store NFL week. Mark them as week 99
            # so they appear in current live summaries, but games_before_week()
            # will exclude them from historical training for any real NFL week.
            log["Week"] = 99.0
            log["Home_Score"] = log["Actual_Home_Score"]
            log["Away_Score"] = log["Actual_Away_Score"]
            frames.append(log[REQUIRED_COLUMNS].copy())

    if not frames:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    games = pd.concat(frames, ignore_index=True)
    for column in ["Season", "Week", "Home_Score", "Away_Score"]:
        games[column] = pd.to_numeric(games[column], errors="coerce")
    for column in ["Home_Team", "Away_Team"]:
        games[column] = games[column].astype(str).str.strip()
    games = games.dropna(subset=["Home_Score", "Away_Score"])
    games = games[games["Home_Score"] != games["Away_Score"]].copy()
    # Remove duplicates if a game appears in both source files.
    games = games.drop_duplicates(
        subset=["Season", "Week", "Home_Team", "Away_Team", "Home_Score", "Away_Score"]
    )
    return games


def games_before_week(games, season, week):
    """Return only games played before the target game's season/week."""
    if games.empty:
        return games.copy()
    season = float(season)
    week = float(week)
    valid = games.dropna(subset=["Season", "Week"])
    return valid[
        (valid["Season"] < season)
        | ((valid["Season"] == season) & (valid["Week"] < week))
    ].copy()


def get_matchup_history_features(home_team, away_team, games):
    """Return model features plus readable streak details, all from prior games."""
    home_team = str(home_team).strip()
    away_team = str(away_team).strip()
    matchup = games[
        ((games["Home_Team"] == home_team) & (games["Away_Team"] == away_team))
        | ((games["Home_Team"] == away_team) & (games["Away_Team"] == home_team))
    ].copy() if not games.empty else pd.DataFrame(columns=REQUIRED_COLUMNS)

    matchup = matchup.dropna(subset=["Season", "Week"]).sort_values(
        ["Season", "Week"], ascending=False
    )

    home_wins = 0
    away_wins = 0
    ties = 0
    results = []  # W/L from the upcoming home team's perspective

    for _, game in matchup.iterrows():
        if game["Home_Score"] > game["Away_Score"]:
            winner = game["Home_Team"]
        elif game["Away_Score"] > game["Home_Score"]:
            winner = game["Away_Team"]
        else:
            winner = "Tie"

        if winner == home_team:
            home_wins += 1
            results.append("W")
        elif winner == away_team:
            away_wins += 1
            results.append("L")
        else:
            ties += 1
            results.append("T")

    total = home_wins + away_wins + ties
    h2h_pct = (home_wins + 0.5 * ties) / total if total else 0.5

    # Positive streak = upcoming home team has won the recent meetings.
    h2h_streak = 0
    if results and results[0] != "T":
        latest = results[0]
        for result in results:
            if result != latest:
                break
            h2h_streak += 1
        if latest == "L":
            h2h_streak *= -1

    venue = matchup[matchup["Home_Team"] == home_team].copy()
    venue_wins = 0
    venue_losses = 0
    venue_ties = 0
    venue_results = []  # W/L from visiting away team's perspective

    for _, game in venue.iterrows():
        if game["Away_Score"] > game["Home_Score"]:
            venue_wins += 1
            venue_results.append("W")
        elif game["Home_Score"] > game["Away_Score"]:
            venue_losses += 1
            venue_results.append("L")
        else:
            venue_ties += 1
            venue_results.append("T")

    venue_total = venue_wins + venue_losses + venue_ties
    home_venue_pct = (venue_losses + 0.5 * venue_ties) / venue_total if venue_total else 0.5

    # Positive streak = visiting team has repeatedly lost at this stadium.
    venue_streak = 0
    if venue_results and venue_results[0] != "T":
        latest_venue = venue_results[0]
        for result in venue_results:
            if result != latest_venue:
                break
            venue_streak += 1
        if latest_venue == "W":
            venue_streak *= -1

    # Cap streaks at five games and scale to [-1, 1] for model stability.
    features = {
        "head_to_head_win_pct": h2h_pct,
        "head_to_head_streak": max(-5, min(5, h2h_streak)) / 5.0,
        "home_venue_win_pct": home_venue_pct,
        "away_venue_streak": max(-5, min(5, venue_streak)) / 5.0,
    }
    details = {
        "head_to_head_record": f"{home_wins}-{away_wins}-{ties}",
        "head_to_head_streak_count": h2h_streak,
        "venue_record_away_team": f"{venue_wins}-{venue_losses}-{venue_ties}",
        "away_venue_streak_count": venue_streak,
        "matchup_games": total,
        "venue_games": venue_total,
    }
    return features, details
