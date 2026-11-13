import os
import pandas as pd

LOG_FILE = "NFL_Game_Log.csv"
BLOWOUT_MARGIN = 14


def load_log():
    if not os.path.exists(LOG_FILE):
        raise FileNotFoundError(
            f"{LOG_FILE} does not exist. Run PredictNFL.py first."
        )
    log = pd.read_csv(LOG_FILE)
    if log.empty:
        raise ValueError("The game log is empty.")
    required = ["Game_ID", "Home_Team", "Away_Team",
                "Predicted_Home_Score", "Predicted_Away_Score",
                "Predicted_Home_Win_Probability"]
    missing = [column for column in required if column not in log.columns]
    if missing:
        raise ValueError("Game log is missing: " + ", ".join(missing))

    for column, default in [
        ("Actual_Winner", ""),
        ("Actual_Home_Score", ""),
        ("Actual_Away_Score", ""),
        ("Actual_Home_Win", ""),
        ("Actual_Margin", ""),
        ("Home_Blowout", ""),
        ("Away_Blowout", ""),
        ("Completed", False),
    ]:
        if column not in log.columns:
            log[column] = default
    return log


def completed_rows(log):
    return log[log["Completed"].astype(str).str.lower().isin(["true", "1"])]


def show_accuracy(log):
    completed = completed_rows(log)
    if completed.empty:
        print("\nNo completed games have been recorded yet.")
        return

    scored = completed.dropna(subset=[
        "Predicted_Home_Score", "Predicted_Away_Score",
        "Actual_Home_Score", "Actual_Away_Score"
    ]).copy()
    if not scored.empty:
        home_mae = (
            scored["Predicted_Home_Score"] - scored["Actual_Home_Score"]
        ).abs().mean()
        away_mae = (
            scored["Predicted_Away_Score"] - scored["Actual_Away_Score"]
        ).abs().mean()
        print(f"\nCompleted games: {len(completed)}")
        print(f"Average absolute home-score error: {home_mae:.2f}")
        print(f"Average absolute away-score error: {away_mae:.2f}")

    evaluated = completed.dropna(
        subset=["Predicted_Home_Win_Probability", "Actual_Home_Win"]
    ).copy()
    evaluated = evaluated[evaluated["Actual_Home_Win"].isin([0, 1])]
    if not evaluated.empty:
        correct = (
            (evaluated["Predicted_Home_Win_Probability"] >= 0.5)
            == (evaluated["Actual_Home_Win"] == 1)
        ).mean()
        brier = (
            evaluated["Predicted_Home_Win_Probability"]
            - evaluated["Actual_Home_Win"]
        ).pow(2).mean()
        print(f"Winner accuracy (non-ties): {correct * 100:.1f}%")
        print(f"Brier score (lower is better): {brier:.4f}")

    blowout_count = (
        (completed["Home_Blowout"] == True)
        | (completed["Away_Blowout"] == True)
    ).sum()
    print(f"Games decided by 14+ points: {blowout_count}")


def main():
    log = load_log()
    pending = log[
        ~log["Completed"].astype(str).str.lower().isin(["true", "1"])
    ]

    if pending.empty:
        print("There are no uncompleted predictions.")
        show_accuracy(log)
        return

    print("\nPredictions awaiting results:")
    for _, row in pending.iterrows():
        print(
            f"Game ID: {row['Game_ID']} | {row['Home_Team']} vs. {row['Away_Team']} | "
            f"Projected {float(row['Predicted_Home_Score']):.1f}-"
            f"{float(row['Predicted_Away_Score']):.1f} | "
            f"Home win chance: {float(row['Predicted_Home_Win_Probability'])*100:.1f}%"
        )

    game_id = input("\nEnter the Game ID to update (or Q to quit): ").strip()
    if game_id.lower() == "q":
        return

    matches = log.index[log["Game_ID"].astype(str) == game_id].tolist()
    if not matches:
        print("Game ID not found. Copy the ID exactly.")
        return

    index = matches[0]
    if str(log.at[index, "Completed"]).lower() in ["true", "1"]:
        print("That game already has a result. No changes were made.")
        return

    home_team = log.at[index, "Home_Team"]
    away_team = log.at[index, "Away_Team"]

    try:
        home_score = int(input(f"Final score for {home_team}: "))
        away_score = int(input(f"Final score for {away_team}: "))
        if home_score < 0 or away_score < 0:
            raise ValueError
    except ValueError:
        print("Scores must be whole numbers greater than or equal to zero.")
        return

    margin = home_score - away_score
    log.at[index, "Actual_Home_Score"] = home_score
    log.at[index, "Actual_Away_Score"] = away_score
    log.at[index, "Actual_Margin"] = margin
    log.at[index, "Completed"] = True

    if margin > 0:
        log.at[index, "Actual_Winner"] = home_team
        log.at[index, "Actual_Home_Win"] = 1
    elif margin < 0:
        log.at[index, "Actual_Winner"] = away_team
        log.at[index, "Actual_Home_Win"] = 0
    else:
        log.at[index, "Actual_Winner"] = "Tie"
        log.at[index, "Actual_Home_Win"] = 0.5

    log.at[index, "Home_Blowout"] = int(margin >= BLOWOUT_MARGIN)
    log.at[index, "Away_Blowout"] = int(margin <= -BLOWOUT_MARGIN)

    log.to_csv(LOG_FILE, index=False)
    print("\nResult saved:")
    print(f"{home_team} {home_score} - {away_team} {away_score}")
    print("Winner:", log.at[index, "Actual_Winner"])
    print(f"Blowout: {'Yes' if abs(margin) >= BLOWOUT_MARGIN else 'No'}")
    print(f"Updated {LOG_FILE}.")

    completed = completed_rows(log)
    non_ties = completed[completed["Actual_Home_Win"].isin([0, 1])]
    print(f"\nCompleted non-tie games available for learning: {len(non_ties)}")
    print("Run TrainNFLModel.py to retrain using the latest results.")
    show_accuracy(log)


if __name__ == "__main__":
    main()
