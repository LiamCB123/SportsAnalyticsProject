import os
import pandas as pd

# ==========================================
# 1. LOAD DATA
# ==========================================

df = pd.read_csv("NFL_Combined.csv")
df.columns = df.columns.astype(str).str.strip()
for col in df.columns:
    if col.startswith("special-teams_"):
        print(col)

# Convert statistical columns to numbers
for column in df.columns:
    if column != "Team":
        df[column] = pd.to_numeric(df[column], errors="coerce")

df["Team"] = df["Team"].astype(str).str.strip()
df = df.drop_duplicates(subset=["Team"]).copy()
df = df.reset_index(drop=True)


# ==========================================
# 2. ENTER GENERAL GAMES PLAYED
# ==========================================

print("\n===================================")
print("       ENTER GAMES PLAYED")
print("===================================")

while True:
    try:
        games_played = int(
            input("How many games have been played this season? ")
        )

        if games_played < 1:
            print("Enter at least 1 game.")
        else:
            break

    except ValueError:
        print("Please enter a whole number.")

# Apply the same number of games to every team
df["Games_Played"] = games_played
# ==========================================
# 3. HELPER TO GET A STATISTIC COLUMN
# ==========================================

def get_stat(column_name):
    if column_name in df.columns:
        return df[column_name].fillna(0)

    return pd.Series(0, index=df.index, dtype=float)


# ==========================================
# 4. ESTIMATE POINTS SCORED
# ==========================================

# Offensive touchdowns
offensive_touchdowns = get_stat(
    "Offense_scoring_Tot TD"
)

# Extra points and field goals
extra_points = get_stat(
    "special-teams_scoring_XPM"
)

field_goals = get_stat(
    "special-teams_scoring_FGM"
)

# Two-point conversions
two_point_conversions = get_stat(
    "Offense_scoring_2-PT"
)

# Defensive touchdowns
fumble_return_tds = get_stat(
    "Defense_scoring_FR TD"
)

interception_return_tds = get_stat(
    "Defense_scoring_INT TD"
)

# Special-teams return touchdowns
kick_return_tds = get_stat(
    "special-teams_scoring_KRet TD"
)

punt_return_tds = get_stat(
    "special-teams_scoring_PRet T"
)

# Safeties scored by the team
safeties = get_stat(
    "Defense_scoring_SFTY"
)

# Estimate points scored by offense
df["Offense_Points"] = (
    offensive_touchdowns * 6
    + extra_points
    + field_goals * 3
    + two_point_conversions * 2
)

# Estimate defensive and return points
df["Defensive_Special_Teams_Points"] = (
    fumble_return_tds * 6
    + interception_return_tds * 6
    + kick_return_tds * 6
    + punt_return_tds * 6
    + safeties * 2
)

# Estimated total team points
df["Estimated_Total_Points_Scored"] = (
    df["Offense_Points"]
    + df["Defensive_Special_Teams_Points"]
)

# Calculate points per game
df["Points_Per_Game"] = (
    df["Estimated_Total_Points_Scored"]
    / df["Games_Played"]
)




# ==========================================
# 5. CALCULATE POINTS ALLOWED
# ==========================================

if "Points_Allowed" not in df.columns:
    raise ValueError(
        "Points_Allowed was not found in NFL_Combined.csv."
    )

# Actual total points allowed
df["PA"] = df["Points_Allowed"]

# Actual points allowed per game
df["PAPG"] = df["PA"] / df["Games_Played"]

# Opponent rushing touchdowns
rushing_tds_allowed = get_stat("Defense_rushing_TD")

# Opponent receiving touchdowns
receiving_tds_allowed = get_stat("Defense_receiving_TD")

# Estimated points allowed from rushing and receiving TDs
df["Rushing_Receiving_TD_Points_Allowed"] = (
    rushing_tds_allowed + receiving_tds_allowed
) * 6

# Remaining points allowed after subtracting TD points
df["Remaining_Points_Allowed"] = (
    df["PA"] - df["Rushing_Receiving_TD_Points_Allowed"]
)

# Remaining points allowed per game
df["Remaining_Points_Allowed_Per_Game"] = (
    df["Remaining_Points_Allowed"] / df["Games_Played"]
)
# ==========================================
# 6. DETERMINE WHETHER LOWER IS BETTER
# ==========================================

def lower_is_better(column):
    name = column.lower()
    category = name.split("_")[0]

    # Offensive turnovers, sacks allowed, and penalties
    if category == "offense":
        return any(word in name for word in [
            "interceptions",
            "_int",
            "fumbles lost",
            "sacks",
            "penalties",
            "penyds"
        ])

    # Defensive touchdowns from interceptions/fumbles,
    # sacks, and safeties are positive defensive plays.
    if category == "defense":
        if any(word in name for word in [
            "scoring_int td",
            "scoring_fr td",
            "sacks",
            "safety"
        ]):
            return False

        # Defensive statistics that are better when lower
        if any(word in name for word in [
            "pass yds",
            "passing_yds",
            "rush yds",
            "rushing_rush yds",
            "receiving_yds",
            "passing_td",
            "rushing_td",
            "receiving_td",
            "yds/att",
            "yds/rec"
        ]):
            return True

    return False


# ==========================================
# 7. CALCULATE CATEGORY SCORES
# ==========================================

def calculate_category_score(
    data,
    prefix,
    exclude_keywords=None
):
    if exclude_keywords is None:
        exclude_keywords = []

    score_columns = {}

    for column in data.columns:

        if not column.startswith(prefix):
            continue

        # Exclude statistics represented by PPG scores
        if any(
            word in column.lower()
            for word in exclude_keywords
        ):
            continue

        # Ignore blank-header columns
        if "nan" in column.lower():
            continue

        # Ignore ranking columns
        last_part = column.split("_")[-1].lower()

        if last_part in ["rk", "rank"]:
            continue

        if not pd.api.types.is_numeric_dtype(data[column]):
            continue

        if data[column].notna().sum() < 2:
            continue

        # Skip duplicate statistics
        duplicate = False

        for previous_column in score_columns:
            if data[column].equals(data[previous_column]):
                duplicate = True
                break

        if duplicate:
            continue

        average = data[column].mean()
        std_dev = data[column].std()

        if pd.isna(std_dev) or std_dev == 0:
            continue

        # Standardize the statistic
        z_score = (data[column] - average) / std_dev

        # Reverse statistics where lower is better
        if lower_is_better(column):
            z_score = -z_score

        score_columns[column] = z_score

    if not score_columns:
        raise ValueError(
            "No usable statistics found for " + prefix
        )

    scores = pd.DataFrame(score_columns, index=data.index)

    return scores.mean(axis=1)


# General offense statistics, excluding scoring totals
df["Offense_Stats_Score"] = calculate_category_score(
    df,
    "Offense_",
    exclude_keywords=["offense_scoring_"]
)

# General defense statistics, excluding the two TD-allowed
# columns so they are not counted again in the PA calculation
df["Defense_Stats_Score"] = calculate_category_score(
    df,
    "Defense_",
    exclude_keywords=[
        "defense_receiving_td",
        "defense_rushing_td"
    ]
)


# ==========================================
# 7. CALCULATE CATEGORY SCORES
# ==========================================

# General offense statistics, excluding scoring totals
df["Offense_Stats_Score"] = calculate_category_score(
    df,
    "Offense_",
    exclude_keywords=["offense_scoring_"]
)

# General defense statistics
df["Defense_Stats_Score"] = calculate_category_score(
    df,
    "Defense_",
    exclude_keywords=[
        "defense_receiving_td",
        "defense_rushing_td"
    ]
)

# ------------------------------------------
# SPECIAL TEAMS SCORE
# ------------------------------------------

# Field goal percentage
fg_percentage = get_stat("special-teams_field-goals_FG%")

# Extra points made per game
xp_made = get_stat("special-teams_scoring_XPM")
df["XP_Per_Game"] = xp_made / df["Games_Played"]

# Average punt yards
punt_average = get_stat("special-teams_punts_AVG")

# Average punt-return and kickoff-return yards
punt_return_average = get_stat(
    "special-teams_punt-returns_AVG"
)

kickoff_return_average = get_stat(
    "special-teams_kickoff-returns_AVG"
)

df["Return_Average"] = (
    punt_return_average + kickoff_return_average
) / 2


# Helper function to standardize a statistic
def standardize_stat(stat, lower_is_better=False):
    std_dev = stat.std()

    if pd.isna(std_dev) or std_dev == 0:
        return pd.Series(0.0, index=df.index)

    score = (stat - stat.mean()) / std_dev

    if lower_is_better:
        score = -score

    return score


# Calculate individual scores
df["FG_Percentage_Score"] = standardize_stat(
    fg_percentage
)

df["XP_Score"] = standardize_stat(
    df["XP_Per_Game"]
)

df["Punt_Score"] = standardize_stat(
    punt_average
)

df["Return_Score"] = standardize_stat(
    df["Return_Average"]
)


# Combine the four special-teams categories
df["Special_Teams_Score"] = (
    df["FG_Percentage_Score"] * 0.35
    + df["XP_Score"] * 0.15
    + df["Punt_Score"] * 0.25
    + df["Return_Score"] * 0.25
)




# ==========================================
# 8. ADD PPG AND POINTS-ALLOWED SCORES
# ==========================================

# Standardize estimated points per game
ppg_std = df["Points_Per_Game"].std()

if pd.isna(ppg_std) or ppg_std == 0:
    raise ValueError("Points per game has no variation.")

df["PPG_Score"] = (
    df["Points_Per_Game"] - df["Points_Per_Game"].mean()
) / ppg_std


# Standardize actual points allowed per game.
# Lower PAPG is better, so reverse the score.
papg_std = df["PAPG"].std()

if pd.isna(papg_std) or papg_std == 0:
    raise ValueError("Points allowed per game has no variation.")

df["PA_Score"] = -(
    df["PAPG"] - df["PAPG"].mean()
) / papg_std


# OFFENSE:
# 60% general offensive statistics
# 40% points per game
df["Offense_Score"] = (
    df["Offense_Stats_Score"] * 0.60
    + df["PPG_Score"] * 0.40
)


# DEFENSE:
# 60% general defensive statistics
# 40% actual points allowed per game
df["Defense_Score"] = (
    df["Defense_Stats_Score"] * 0.60
    + df["PA_Score"] * 0.40
)

# ==========================================
# 9. OVERALL RANKING
# ==========================================

# Original weights: 50% offense, 40% defense,
# and 10% special teams.
df["Overall_Score"] = (
    df["Offense_Score"] * 0.50
    + df["Defense_Score"] * 0.40
    + df["Special_Teams_Score"] * 0.10
)

df = df.sort_values(
    "Overall_Score",
    ascending=False
).reset_index(drop=True)

df["Rank"] = df.index + 1



# ==========================================
# 10. DISPLAY NFL TEAM RANKINGS
# ==========================================

print("\n===================================")
print("          NFL TEAM RANKINGS")
print("===================================\n")

print(
    df[[
        "Rank",
        "Team",
        "Games_Played",
        "Points_Per_Game",
        "PA",
        "PAPG",
        "Offense_Score",
        "Defense_Score",
        "Special_Teams_Score",
        "Overall_Score"
    ]].rename(columns={
        "Points_Per_Game": "PPG"
    }).round(2).to_string(index=False)
)

# ==========================================
# 11. DISPLAY YARDAGE STATS
# ==========================================

yard_columns = []

for column in df.columns:
    name = column.lower()

    if "nan" in name:
        continue

    if column in [
        "Offense_Score",
        "Defense_Score",
        "Special_Teams_Score",
        "Overall_Score",
        "Rank"
    ]:
        continue

    if any(word in name for word in ["yds", "yards"]):
        yard_columns.append(column)

# Remove columns with identical values
unique_yard_columns = []

for column in yard_columns:
    duplicate = False

    for previous_column in unique_yard_columns:
        if df[column].equals(df[previous_column]):
            duplicate = True
            break

    if not duplicate:
        unique_yard_columns.append(column)

print("\n===================================")
print("          NFL YARDAGE STATS")
print("===================================\n")

if unique_yard_columns:
    print(
        df[["Rank", "Team"] + unique_yard_columns]
        .round(2)
        .to_string(index=False)
    )
else:
    print("No yardage columns found.")




# ==========================================
# 12. DISPLAY SCORING AND POINTS
# ==========================================

print("\n===================================")
print("       NFL SCORING AND POINTS")
print("===================================\n")

print(
    df[[
        "Rank",
        "Team",
        "Games_Played",
        "Estimated_Total_Points_Scored",
        "Points_Per_Game",
        "PA",
        "PAPG",
        "Rushing_Receiving_TD_Points_Allowed",
        "Remaining_Points_Allowed",
        "Remaining_Points_Allowed_Per_Game"
    ]].rename(columns={
        "Estimated_Total_Points_Scored": "Est_Total_Points",
        "Points_Per_Game": "PPG",
        "Rushing_Receiving_TD_Points_Allowed": "Rush_Rec_TD_PA",
        "Remaining_Points_Allowed": "Remaining_PA",
        "Remaining_Points_Allowed_Per_Game": "Remaining_PAPG"
    }).round(2).to_string(index=False)
)

# ==========================================
# 13. SAVE RESULTS
# ==========================================

df.to_csv("NFL_Team_Rankings.csv", index=False)

print("\nSaved NFL_Team_Rankings.csv")

# ==========================================
# 14. SAVE RANKINGS REPORT
# ==========================================

report_file = "NFL_Rankings_Report.xlsx"
history_file = "NFL_Ranking_History.csv"

# ------------------------------------------
# TOP 5 OFFENSES
# ------------------------------------------

top_5_offense = df.sort_values(
    by="Offense_Score",
    ascending=False
).head(5)

top_5_offense = top_5_offense[
    ["Team", "Offense_Score", "Rank"]
].reset_index(drop=True)

top_5_offense.insert(
    0, "Offense_Rank", range(1, len(top_5_offense) + 1)
)

# ------------------------------------------
# TOP 5 DEFENSES
# ------------------------------------------

top_5_defense = df.sort_values(
    by="Defense_Score",
    ascending=False
).head(5)

top_5_defense = top_5_defense[
    ["Team", "Defense_Score", "Rank"]
].reset_index(drop=True)

top_5_defense.insert(
    0, "Defense_Rank", range(1, len(top_5_defense) + 1)
)

# ------------------------------------------
# TOP 5 SPECIAL TEAMS
# ------------------------------------------

top_5_special_teams = df.sort_values(
    by="Special_Teams_Score",
    ascending=False
).head(5)

top_5_special_teams = top_5_special_teams[
    ["Team", "Special_Teams_Score", "Rank"]
].reset_index(drop=True)

top_5_special_teams.insert(
    0, "Special_Teams_Rank",
    range(1, len(top_5_special_teams) + 1)
)

# ------------------------------------------
# ALL TEAMS
# ------------------------------------------

all_teams = df.sort_values(
    by="Rank",
    ascending=True
)

all_teams = all_teams[
    [
        "Rank",
        "Team",
        "Offense_Score",
        "Defense_Score",
        "Special_Teams_Score",
        "Overall_Score"
    ]
].reset_index(drop=True)

# ------------------------------------------
# SAVE EXCEL REPORT
# ------------------------------------------

with pd.ExcelWriter(report_file, engine="openpyxl") as writer:

    top_5_offense.to_excel(
        writer,
        sheet_name="Top 5 Offense",
        index=False
    )

    top_5_defense.to_excel(
        writer,
        sheet_name="Top 5 Defense",
        index=False
    )

    top_5_special_teams.to_excel(
        writer,
        sheet_name="Top 5 Special Teams",
        index=False
    )

    all_teams.to_excel(
        writer,
        sheet_name="All 32 Teams",
        index=False
    )

print("\nSaved " + report_file)

# ==========================================
# 15. SAVE RANKING HISTORY
# ==========================================

season = int(input("Enter NFL season year (example 2026): "))
week = int(input("Enter NFL week number: "))

snapshot = df[
    [
        "Rank",
        "Team",
        "Offense_Score",
        "Defense_Score",
        "Special_Teams_Score",
        "Overall_Score"
    ]
].copy()

snapshot["Season"] = season
snapshot["Week"] = week

if os.path.exists(history_file):

    history = pd.read_csv(history_file)

    # Replace this season/week if it was saved previously
    history = history[
        ~(
            (history["Season"] == season) &
            (history["Week"] == week)
        )
    ]

    history = pd.concat(
        [history, snapshot],
        ignore_index=True,
        sort=False
    )

else:
    history = snapshot

history = history.sort_values(
    by=["Season", "Week", "Rank"]
).reset_index(drop=True)

history.to_csv(history_file, index=False)

print("Saved " + history_file)
print("Ranking report and history updated successfully.")
