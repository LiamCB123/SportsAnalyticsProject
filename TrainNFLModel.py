"""
TrainNFLModel.py

Trains win and blowout probability models using:
1. Completed games already saved in NFL_Game_Log.csv.
2. Optional multi-season results in NFL_Historical_Games.csv.

Historical results must use pregame rankings. The script matches each game
to the latest ranking snapshot from an earlier week in the same season.
"""

import json
import os
import math

import pandas as pd

from NFL_Matchup_History import (
    matchup_type_features, get_matchup_history_features, games_before_week
)

LOG_FILE = "NFL_Game_Log.csv"
HISTORY_FILE = "NFL_Ranking_History.csv"
HISTORICAL_GAMES_FILE = "NFL_Historical_Games.csv"
MODEL_FILE = "NFL_Model_Weights.json"

MIN_GAMES = 30
BLOWOUT_MARGIN = 14
RECENCY_DECAY = 0.85

FEATURE_COLUMNS = [
    "rank_advantage",
    "ppg_difference",
    "defense_difference",
    "overall_difference",
    "same_division",
    "same_conference",
    "head_to_head_win_pct",
    "head_to_head_streak",
    "home_venue_win_pct",
    "away_venue_streak",
]

TEAM_DIVISIONS = {
    "Bills": "AFC East", "Dolphins": "AFC East",
    "Patriots": "AFC East", "Jets": "AFC East",
    "Ravens": "AFC North", "Bengals": "AFC North",
    "Browns": "AFC North", "Steelers": "AFC North",
    "Texans": "AFC South", "Colts": "AFC South",
    "Jaguars": "AFC South", "Titans": "AFC South",
    "Broncos": "AFC West", "Chiefs": "AFC West",
    "Raiders": "AFC West", "Chargers": "AFC West",
    "Cowboys": "NFC East", "Giants": "NFC East",
    "Eagles": "NFC East", "Commanders": "NFC East",
    "Bears": "NFC North", "Lions": "NFC North",
    "Packers": "NFC North", "Vikings": "NFC North",
    "Falcons": "NFC South", "Panthers": "NFC South",
    "Saints": "NFC South", "Buccaneers": "NFC South",
    "Cardinals": "NFC West", "Rams": "NFC West",
    "49ers": "NFC West", "Seahawks": "NFC West",
}


def logistic(value):
    value = max(-30, min(30, float(value)))
    return 1.0 / (1.0 + math.exp(-value))


def same_division(home, away):
    return matchup_type_features(home, away)["same_division"] == 1


def safe_number(row, column, default=0.0):
    value = row.get(column, default)
    try:
        number = float(value)
        if pd.isna(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def build_features(home, away, home_team, away_team, prior_games):
    home_rank = safe_number(home, "Rank", 16.5)
    away_rank = safe_number(away, "Rank", 16.5)

    home_overall = safe_number(home, "Overall_Score")
    away_overall = safe_number(away, "Overall_Score")

    # Older ranking-history snapshots may not have PPG/PAPG.
    home_ppg = safe_number(home, "Points_Per_Game", float("nan"))
    away_ppg = safe_number(away, "Points_Per_Game", float("nan"))
    if not math.isnan(home_ppg) and not math.isnan(away_ppg):
        ppg_difference = (home_ppg - away_ppg) / 10.0
    else:
        ppg_difference = (
            safe_number(home, "Offense_Score")
            - safe_number(away, "Offense_Score")
        )

    home_papg = safe_number(home, "PAPG", float("nan"))
    away_papg = safe_number(away, "PAPG", float("nan"))
    if not math.isnan(home_papg) and not math.isnan(away_papg):
        defense_difference = (away_papg - home_papg) / 10.0
    else:
        defense_difference = (
            safe_number(home, "Defense_Score")
            - safe_number(away, "Defense_Score")
        )

    type_features = matchup_type_features(home_team, away_team)
    history_features, _ = get_matchup_history_features(
        home_team, away_team, prior_games
    )

    return {
        "rank_advantage": (away_rank - home_rank) / 31.0,
        "ppg_difference": ppg_difference,
        "defense_difference": defense_difference,
        "overall_difference": home_overall - away_overall,
        **type_features,
        **history_features,
    }


def add_completed_log_games(rows):
    if not os.path.exists(LOG_FILE):
        return

    log = pd.read_csv(LOG_FILE)
    if log.empty or "Actual_Home_Score" not in log.columns:
        return

    if "Completed" in log.columns:
        log = log[log["Completed"].astype(str).str.lower().isin(["true", "1"])]

    for _, game in log.iterrows():
        try:
            home_score = float(game["Actual_Home_Score"])
            away_score = float(game["Actual_Away_Score"])
        except (TypeError, ValueError):
            continue
        if pd.isna(home_score) or pd.isna(away_score):
            continue
        if home_score == away_score:
            continue

        # New predictions save these features at prediction time. Older rows
        # did not, so they receive neutral head-to-head values rather than
        # accidentally using results that happened after the prediction.
        type_features = matchup_type_features(game["Home_Team"], game["Away_Team"])
        features = {
            "rank_advantage": safe_number(game, "rank_advantage"),
            "ppg_difference": safe_number(game, "ppg_difference"),
            "defense_difference": safe_number(game, "defense_difference"),
            "overall_difference": safe_number(game, "overall_difference"),
            **type_features,
            "head_to_head_win_pct": safe_number(game, "head_to_head_win_pct", 0.5),
            "head_to_head_streak": safe_number(game, "head_to_head_streak", 0.0),
            "home_venue_win_pct": safe_number(game, "home_venue_win_pct", 0.5),
            "away_venue_streak": safe_number(game, "away_venue_streak", 0.0),
        }
        rows.append({
            **features,
            "home_win": 1.0 if home_score > away_score else 0.0,
            "home_blowout": 1.0 if home_score - away_score >= BLOWOUT_MARGIN else 0.0,
            "away_blowout": 1.0 if away_score - home_score >= BLOWOUT_MARGIN else 0.0,
            "season": int(str(game.get("Prediction_Date", "2026"))[:4])
                if str(game.get("Prediction_Date", ""))[:4].isdigit() else 2026,
        })


def add_historical_games(rows):
    if not os.path.exists(HISTORICAL_GAMES_FILE):
        print(f"{HISTORICAL_GAMES_FILE} not found; using completed game log only.")
        return

    if not os.path.exists(HISTORY_FILE):
        print(f"{HISTORY_FILE} not found; cannot match historical results to pregame rankings.")
        return

    games = pd.read_csv(HISTORICAL_GAMES_FILE)
    history = pd.read_csv(HISTORY_FILE)

    required_games = [
        "Season", "Week", "Home_Team", "Away_Team",
        "Home_Score", "Away_Score",
    ]
    missing = [column for column in required_games if column not in games.columns]
    if missing:
        raise ValueError(
            f"{HISTORICAL_GAMES_FILE} is missing columns: {', '.join(missing)}"
        )

    required_history = ["Season", "Week", "Team", "Rank", "Overall_Score"]
    missing = [column for column in required_history if column not in history.columns]
    if missing:
        raise ValueError(
            f"{HISTORY_FILE} is missing columns: {', '.join(missing)}"
        )

    for column in ["Season", "Week", "Rank", "Overall_Score"]:
        history[column] = pd.to_numeric(history[column], errors="coerce")
    games["Season"] = pd.to_numeric(games["Season"], errors="coerce")
    games["Week"] = pd.to_numeric(games["Week"], errors="coerce")

    history["Team"] = history["Team"].astype(str).str.strip()
    games["Home_Team"] = games["Home_Team"].astype(str).str.strip()
    games["Away_Team"] = games["Away_Team"].astype(str).str.strip()

    # Include only completed historical games when building prior matchup trends.
    for column in ["Home_Score", "Away_Score"]:
        games[column] = pd.to_numeric(games[column], errors="coerce")
    games = games.dropna(subset=["Season", "Week", "Home_Score", "Away_Score"])

    added = 0
    for _, game in games.iterrows():
        if pd.isna(game["Season"]) or pd.isna(game["Week"]):
            continue
        try:
            home_score = float(game["Home_Score"])
            away_score = float(game["Away_Score"])
        except (TypeError, ValueError):
            continue
        if pd.isna(home_score) or pd.isna(away_score) or home_score == away_score:
            continue

        # Strictly use a snapshot from an earlier week, never the same/future week.
        prior = history[
            (history["Season"] == game["Season"])
            & (history["Week"] < game["Week"])
        ]
        if prior.empty:
            continue

        snapshot_week = prior["Week"].max()
        snapshot = prior[prior["Week"] == snapshot_week].set_index("Team")
        home_team = game["Home_Team"]
        away_team = game["Away_Team"]
        if home_team not in snapshot.index or away_team not in snapshot.index:
            continue

        prior_games = games_before_week(games, game["Season"], game["Week"])
        features = build_features(
            snapshot.loc[home_team], snapshot.loc[away_team],
            home_team, away_team, prior_games
        )
        rows.append({
            **features,
            "home_win": 1.0 if home_score > away_score else 0.0,
            "home_blowout": 1.0 if home_score - away_score >= BLOWOUT_MARGIN else 0.0,
            "away_blowout": 1.0 if away_score - home_score >= BLOWOUT_MARGIN else 0.0,
            "season": int(game["Season"]),
        })
        added += 1

    print(f"Historical games matched to earlier ranking snapshots: {added}")


def fit_logistic_model(data, target_column):
    x = data[FEATURE_COLUMNS].astype(float).values
    y = data[target_column].astype(float).values
    sample_weights = data["sample_weight"].astype(float).values

    means = x.mean(axis=0)
    scales = x.std(axis=0)
    scales[scales == 0] = 1.0
    x = (x - means) / scales

    weights = [0.0] * (len(FEATURE_COLUMNS) + 1)
    learning_rate = 0.05
    regularization = 0.02
    total_weight = sample_weights.sum()

    for _ in range(4000):
        gradients = [0.0] * len(weights)
        for row, target, sample_weight in zip(x, y, sample_weights):
            z = weights[0]
            for index, value in enumerate(row):
                z += weights[index + 1] * value
            error = (logistic(z) - target) * sample_weight
            gradients[0] += error
            for index, value in enumerate(row):
                gradients[index + 1] += error * value

        for index in range(len(weights)):
            gradients[index] /= total_weight
            if index > 0:
                gradients[index] += regularization * weights[index]
            weights[index] -= learning_rate * gradients[index]

    return {
        "means": means.tolist(),
        "scales": scales.tolist(),
        "weights": weights,
    }


def main():
    rows = []
    add_completed_log_games(rows)
    add_historical_games(rows)

    if not rows:
        print("No completed games could be used for training.")
        print(f"Complete predictions in {LOG_FILE} or add {HISTORICAL_GAMES_FILE}.")
        return

    data = pd.DataFrame(rows)
    data = data.dropna(subset=FEATURE_COLUMNS + ["home_win"])
    data["season"] = pd.to_numeric(data["season"], errors="coerce").fillna(2026)

    latest_season = int(data["season"].max())
    data["sample_weight"] = data["season"].apply(
        lambda season: RECENCY_DECAY ** max(0, latest_season - int(season))
    )

    if len(data) < MIN_GAMES:
        print(f"Only {len(data)} usable games found; need at least {MIN_GAMES}.")
        print("Add completed results from more seasons, then run this script again.")
        return

    models = {}
    targets = ["home_win", "home_blowout", "away_blowout"]
    for target in targets:
        models[target] = fit_logistic_model(data, target)

    # Report an in-sample Brier score as a basic diagnostic, not a validation result.
    win_model = models["home_win"]
    probabilities = []
    for _, row in data.iterrows():
        z = win_model["weights"][0]
        for index, feature in enumerate(FEATURE_COLUMNS):
            value = (
                row[feature] - win_model["means"][index]
            ) / win_model["scales"][index]
            z += win_model["weights"][index + 1] * value
        probabilities.append(logistic(z))
    brier = ((pd.Series(probabilities) - data["home_win"]) ** 2).mean()

    output = {
        "feature_columns": FEATURE_COLUMNS,
        "training_games": int(len(data)),
        "seasons_used": sorted(data["season"].astype(int).unique().tolist()),
        "latest_season": latest_season,
        "recency_decay": RECENCY_DECAY,
        "blowout_margin": BLOWOUT_MARGIN,
        **models,
    }

    with open(MODEL_FILE, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=4)

    print("\nNFL model training complete.")
    print("Games used:", len(data))
    print("Seasons used:", output["seasons_used"])
    print(f"In-sample win-probability Brier score: {brier:.4f}")
    print("Saved:", MODEL_FILE)
    print("\nRun PredictNFL.py to use the trained win and blowout models.")
    print("Important: the Brier score above is in-sample, not a test-set score.")


if __name__ == "__main__":
    main()
