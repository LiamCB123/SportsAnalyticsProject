import csv
import json
import math
import os
from datetime import datetime

import pandas as pd

from NFL_Matchup_History import (
    load_matchup_games, matchup_type_features, get_matchup_history_features
)

RANKINGS_FILE = "NFL_Category_Rankings.csv"
LOG_FILE = "NFL_Game_Log.csv"
MODEL_FILE = "NFL_Model_Weights.json"

# Starting assumptions. These can be improved as you collect results.
HOME_FIELD_POINTS = 1.5
RATING_POINTS_FACTOR = 2.0
PROBABILITY_SCALE = 6.5
DIVISIONAL_MARGIN_FACTOR = 0.85  # Shrinks projected margin for divisional games.
MIN_GAMES_FOR_LEARNED_MODEL = 20

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

# Team names must match the names in NFL_Category_Rankings.csv.
TEAM_DIVISIONS = {
    # AFC East
    "Bills": "AFC East", "Dolphins": "AFC East",
    "Patriots": "AFC East", "Jets": "AFC East",
    # AFC North
    "Ravens": "AFC North", "Bengals": "AFC North",
    "Browns": "AFC North", "Steelers": "AFC North",
    # AFC South
    "Texans": "AFC South", "Colts": "AFC South",
    "Jaguars": "AFC South", "Titans": "AFC South",
    # AFC West
    "Broncos": "AFC West", "Chiefs": "AFC West",
    "Raiders": "AFC West", "Chargers": "AFC West",
    # NFC East
    "Cowboys": "NFC East", "Giants": "NFC East",
    "Eagles": "NFC East", "Commanders": "NFC East",
    # NFC North
    "Bears": "NFC North", "Lions": "NFC North",
    "Packers": "NFC North", "Vikings": "NFC North",
    # NFC South
    "Falcons": "NFC South", "Panthers": "NFC South",
    "Saints": "NFC South", "Buccaneers": "NFC South",
    # NFC West
    "Cardinals": "NFC West", "Rams": "NFC West",
    "49ers": "NFC West", "Seahawks": "NFC West",
}

TEAM_CONFERENCES = {
    team: division.split()[0] for team, division in TEAM_DIVISIONS.items()
}


def matchup_features(home_team, away_team):
    return matchup_type_features(home_team, away_team)


def add_historical_matchup_features(log):
    # Older game logs won't have these new columns, so calculate them from team names.
    if "Home_Team" not in log.columns or "Away_Team" not in log.columns:
        return log

    matchup_values = [
        matchup_features(home, away)
        for home, away in zip(log["Home_Team"], log["Away_Team"])
    ]
    log["same_division"] = [item["same_division"] for item in matchup_values]
    log["same_conference"] = [item["same_conference"] for item in matchup_values]
    for column, default in [("head_to_head_win_pct", 0.5), ("head_to_head_streak", 0.0),
                            ("home_venue_win_pct", 0.5), ("away_venue_streak", 0.0)]:
        if column not in log.columns:
            log[column] = default
        else:
            log[column] = pd.to_numeric(log[column], errors="coerce").fillna(default)
    return log


def logistic(value):
    # Avoid math.exp overflow for unusually large values.
    value = max(-30, min(30, value))
    return 1.0 / (1.0 + math.exp(-value))


def load_rankings():
    if not os.path.exists(RANKINGS_FILE):
        raise FileNotFoundError(
            f"Could not find {RANKINGS_FILE}. "
            "Put PredictNFL.py in the same folder as this CSV."
        )

    df = pd.read_csv(RANKINGS_FILE)
    df["Team"] = df["Team"].astype(str).str.strip()

    required = [
        "Team", "Rank", "Overall_Score",
        "Points_Per_Game", "PAPG"
    ]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(
            "Missing required columns in NFL_Team_Rankings.csv: "
            + ", ".join(missing)
        )

    for column in required[1:]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=required).drop_duplicates(subset=["Team"])
    return df


def get_team(df, name):
    matches = df[df["Team"].str.casefold() == name.casefold()]
    if matches.empty:
        return None
    return matches.iloc[0]


def get_learned_model():
    """Load the trained historical model first, otherwise fit from the game log."""
    if os.path.exists(MODEL_FILE):
        try:
            with open(MODEL_FILE, "r", encoding="utf-8") as file:
                saved_model = json.load(file)
            if saved_model.get("feature_columns") == FEATURE_COLUMNS:
                model = saved_model.get("home_win", {})
                if all(key in model for key in ["means", "scales", "weights"]):
                    return {
                        "weights": model["weights"],
                        "means": model["means"],
                        "scales": model["scales"],
                        "standardized": True,
                    }, int(saved_model.get("training_games", 0))
        except (OSError, ValueError, TypeError, KeyError):
            pass

    if not os.path.exists(LOG_FILE):
        return None, 0

    try:
        log = pd.read_csv(LOG_FILE)
    except pd.errors.EmptyDataError:
        return None, 0

    if "Actual_Home_Win" not in log.columns:
        return None, 0

    # Add new matchup features to older logs too, so previous results remain usable.
    log = add_historical_matchup_features(log)

    for column in FEATURE_COLUMNS:
        if column not in log.columns:
            log[column] = 0

    log["Actual_Home_Win"] = pd.to_numeric(
        log["Actual_Home_Win"], errors="coerce"
    )
    completed = log.dropna(subset=FEATURE_COLUMNS + ["Actual_Home_Win"]).copy()
    # Exclude ties and any invalid outcome from win/loss probability training.
    completed = completed[completed["Actual_Home_Win"].isin([0, 1])]
    if len(completed) < MIN_GAMES_FOR_LEARNED_MODEL:
        return None, len(completed)

    x = completed[FEATURE_COLUMNS].astype(float).values.tolist()
    y = completed["Actual_Home_Win"].astype(float).tolist()

    # Standardized features are already roughly scaled in predict_game().
    # Fit coefficients with batch gradient descent; no scikit-learn needed.
    weights = [0.0] * (len(FEATURE_COLUMNS) + 1)  # intercept + one weight per feature
    learning_rate = 0.08
    regularization = 0.01
    count = len(y)

    for _ in range(2500):
        gradients = [0.0] * len(weights)

        for row, target in zip(x, y):
            z = weights[0]
            for j, feature in enumerate(row):
                z += weights[j + 1] * feature
            probability = logistic(z)
            error = probability - target

            gradients[0] += error
            for j, feature in enumerate(row):
                gradients[j + 1] += error * feature

        for j in range(len(weights)):
            gradients[j] /= count
            if j > 0:
                gradients[j] += regularization * weights[j]
            weights[j] -= learning_rate * gradients[j]

    return {
        "weights": weights,
        "means": [0.0] * len(FEATURE_COLUMNS),
        "scales": [1.0] * len(FEATURE_COLUMNS),
        "standardized": False,
    }, count


def predict_game(df, home_name, away_name):
    home = get_team(df, home_name)
    away = get_team(df, away_name)

    if home is None:
        print(f"Could not find home team '{home_name}'. Check the team names printed above.")
        return
    if away is None:
        print(f"Could not find away team '{away_name}'. Check the team names printed above.")
        return
    if home["Team"] == away["Team"]:
        print("Choose two different teams.")
        return

    # Positive feature values mean the home team has the advantage.
    history_games = load_matchup_games()
    history_features, history_details = get_matchup_history_features(
        home["Team"], away["Team"], history_games
    )

    features = {
        "rank_advantage": (float(away["Rank"]) - float(home["Rank"])) / 31.0,
        "ppg_difference": (float(home["Points_Per_Game"]) - float(away["Points_Per_Game"])) / 10.0,
        "defense_difference": (float(away["PAPG"]) - float(home["PAPG"])) / 10.0,
        "overall_difference": float(home["Overall_Score"]) - float(away["Overall_Score"]),
        **matchup_features(home["Team"], away["Team"]),
        **history_features,
    }

    # Simple initial score projection: blend each team's scoring average
    # with the opponent's points allowed per game.
    home_points = (float(home["Points_Per_Game"]) + float(away["PAPG"])) / 2.0
    away_points = (float(away["Points_Per_Game"]) + float(home["PAPG"])) / 2.0

    rating_adjustment = features["overall_difference"] * RATING_POINTS_FACTOR
    home_points += HOME_FIELD_POINTS / 2.0 + rating_adjustment / 2.0
    away_points -= HOME_FIELD_POINTS / 2.0 + rating_adjustment / 2.0

    home_points = max(0.0, home_points)
    away_points = max(0.0, away_points)
    point_margin = home_points - away_points


    weights, learned_games = get_learned_model()

    if weights is not None:
        z = weights["weights"][0]

        for i, feature_name in enumerate(FEATURE_COLUMNS):
            value = float(features[feature_name])

            if weights["standardized"]:
                value = (value - weights["means"][i]) / weights["scales"][i]

            z += weights["weights"][i + 1] * value

        # Get the confidence level from the trained model.
        model_probability = logistic(z)

        # Preserve the model's confidence, but make its direction
        # agree with the projected point margin.
        confidence = abs(math.log(
            max(0.000001, min(0.999999, model_probability)) /
            (1 - max(0.000001, min(0.999999, model_probability)))
        ))

        if point_margin > 0:
            home_probability = logistic(confidence)
        elif point_margin < 0:
            home_probability = logistic(-confidence)
        else:
            home_probability = 0.5

        probability_source = (
            f"historically trained model, aligned with projected score "
            f"({learned_games} games)"
        )

    else:
        probability_margin = point_margin

        if features["same_division"]:
            probability_margin *= DIVISIONAL_MARGIN_FACTOR

        home_probability = logistic(
            probability_margin / PROBABILITY_SCALE
        )

        probability_source = (
            f"initial formula ({learned_games}/{MIN_GAMES_FOR_LEARNED_MODEL} "
            "completed games available for training)"
        )

        if features["same_division"]:
            probability_source += "; divisional uncertainty adjustment applied"

    away_probability = 1.0 - home_probability

    print("\n" + "=" * 48)
    print("NFL GAME PREDICTION")
    print("=" * 48)
    matchup = matchup_features(home["Team"], away["Team"])
    if matchup["same_division"]:
        matchup_label = "Divisional matchup"
    elif matchup["same_conference"]:
        matchup_label = "Same-conference matchup"
    else:
        matchup_label = "Interconference matchup"

    print(f"Matchup: {home['Team']} (home) vs. {away['Team']} (away)")
    print(f"Matchup type: {matchup_label}")
    print(f"Head-to-head record (home team perspective): {history_details['head_to_head_record']}")
    print(f"Recent head-to-head streak: {history_details['head_to_head_streak_count']} "
          f"({'home team wins' if history_details['head_to_head_streak_count'] > 0 else 'away team wins' if history_details['head_to_head_streak_count'] < 0 else 'none'})")
    print(f"Away-team record at this stadium: {history_details['venue_record_away_team']}")
    print(f"Away-team stadium streak: {history_details['away_venue_streak_count']} "
          f"({'consecutive losses' if history_details['away_venue_streak_count'] > 0 else 'consecutive wins' if history_details['away_venue_streak_count'] < 0 else 'none'})")
    if history_details["matchup_games"] == 0:
        print("Head-to-head history: no historical results loaded for this matchup.")
    print(f"{home['Team']} rank: #{int(home['Rank'])}")
    print(f"{away['Team']} rank: #{int(away['Rank'])}")
    print(f"Projected score: {home['Team']} {round(home_points)} - {away['Team']} {round(away_points)}")
    print(f"Projected point margin (home perspective): {point_margin:.1f}")
    print(f"{home['Team']} win probability: {home_probability * 100:.1f}%")
    print(f"{away['Team']} win probability: {away_probability * 100:.1f}%")
    print(f"Probability method: {probability_source}")

    if abs(home_probability - 0.5) < 0.0001:
        predicted_winner = "Even matchup"
    else:
        predicted_winner = home["Team"] if home_probability > 0.5 else away["Team"]
    print(f"Predicted winner: {predicted_winner}")

    # Save the prediction and the exact pregame inputs used.
    # A saved prediction is not overwritten when the actual result is entered.
    log_row = {
        "Game_ID": datetime.now().strftime("%Y%m%d%H%M%S%f"),
        "Prediction_Date": datetime.now().isoformat(timespec="seconds"),
        "Home_Team": home["Team"],
        "Away_Team": away["Team"],
        "Home_Rank": int(home["Rank"]),
        "Away_Rank": int(away["Rank"]),
        "Home_Overall_Score": float(home["Overall_Score"]),
        "Away_Overall_Score": float(away["Overall_Score"]),
        "Home_PPG": float(home["Points_Per_Game"]),
        "Away_PPG": float(away["Points_Per_Game"]),
        "Home_PAPG": float(home["PAPG"]),
        "Away_PAPG": float(away["PAPG"]),
        **features,
        "Predicted_Home_Score": round(home_points, 2),
        "Predicted_Away_Score": round(away_points, 2),
        "Predicted_Home_Win_Probability": round(home_probability, 6),
        "Predicted_Away_Win_Probability": round(away_probability, 6),
        "Probability_Method": probability_source,
        "Actual_Home_Score": "",
        "Actual_Away_Score": "",
        "Actual_Winner": "",
        "Actual_Home_Win": "",
        "Completed": False,
    }

    if os.path.exists(LOG_FILE):
        try:
            old_log = pd.read_csv(LOG_FILE)
            all_columns = list(dict.fromkeys(list(old_log.columns) + list(log_row.keys())))
            old_log = old_log.reindex(columns=all_columns)
            new_row = pd.DataFrame([log_row]).reindex(columns=all_columns)
            combined = pd.concat([old_log, new_row], ignore_index=True)
        except pd.errors.EmptyDataError:
            combined = pd.DataFrame([log_row])
    else:
        combined = pd.DataFrame([log_row])

    combined.to_csv(LOG_FILE, index=False)
    print(f"\nSaved prediction to {LOG_FILE}.")
    print(f"Game ID: {log_row['Game_ID']}")
    print("Keep this ID so you can enter the final score later.")


def main():
    df = load_rankings()
    print(f"\nTeams found in {RANKINGS_FILE}:")
    for team in sorted(df["Team"].tolist()):
        print("-", team)

    print("\nEnter the matchup. The first team is the home team.")
    home_team = input("Home team: ").strip()
    away_team = input("Away team: ").strip()
    predict_game(df, home_team, away_team)


if __name__ == "__main__":
    main()
#streamlit run NFL_Dashboard.py