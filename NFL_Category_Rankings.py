
import pandas as pd

# ==========================================
# 1. LOAD NFL TEAM RANKINGS
# ==========================================

df = pd.read_csv("NFL_Team_Rankings.csv")

# Remove extra spaces from column names
df.columns = df.columns.astype(str).str.strip()

# Remove duplicate teams
df["Team"] = df["Team"].astype(str).str.strip()
df = df.drop_duplicates(subset=["Team"]).copy()


# ==========================================
# 2. RANK EACH CATEGORY
# ==========================================

# Higher scores receive better rankings
df["Offense_Rank"] = (
    df["Offense_Score"]
    .rank(ascending=False, method="min")
    .astype(int)
)

df["Defense_Rank"] = (
    df["Defense_Score"]
    .rank(ascending=False, method="min")
    .astype(int)
)

df["Special_Teams_Rank"] = (
    df["Special_Teams_Score"]
    .rank(ascending=False, method="min")
    .astype(int)
)


# ==========================================
# 3. DISPLAY OFFENSE RANKINGS
# ==========================================

print("\n===================================")
print("          NFL OFFENSE RANKINGS")
print("===================================\n")

offense_rankings = df.sort_values(
    "Offense_Rank"
)

print(
    offense_rankings[
        [
            "Offense_Rank",
            "Team",
            "Offense_Score",
            "Points_Per_Game"
        ]
    ].rename(
        columns={
            "Points_Per_Game": "PPG"
        }
    ).round(2).to_string(index=False)
)


# ==========================================
# 4. DISPLAY DEFENSE RANKINGS
# ==========================================

print("\n===================================")
print("          NFL DEFENSE RANKINGS")
print("===================================\n")

defense_rankings = df.sort_values(
    "Defense_Rank"
)

print(
    defense_rankings[
        [
            "Defense_Rank",
            "Team",
            "Defense_Score",
            "PAPG"
        ]
    ].rename(
        columns={
            "PAPG": "Points_Allowed_Per_Game"
        }
    ).round(2).to_string(index=False)
)


# ==========================================
# 5. DISPLAY SPECIAL TEAMS RANKINGS
# ==========================================

print("\n===================================")
print("      NFL SPECIAL TEAMS RANKINGS")
print("===================================\n")

special_teams_rankings = df.sort_values(
    "Special_Teams_Rank"
)

print(
    special_teams_rankings[
        [
            "Special_Teams_Rank",
            "Team",
            "Special_Teams_Score"
        ]
    ].round(2).to_string(index=False)
)


# ==========================================
# 6. SAVE CATEGORY RANKINGS
# ==========================================

df = df.sort_values(
    "Overall_Score",
    ascending=False
)

df.to_csv(
    "NFL_Category_Rankings.csv",
    index=False
)

print("\nSaved NFL_Category_Rankings.csv")