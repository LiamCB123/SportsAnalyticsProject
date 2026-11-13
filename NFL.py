
import pandas as pd

# Read the original Excel file
df = pd.read_excel("NFL.xlsx")

team_stats = []


# Clean team names such as "SaintsSaints" into "Saints"
def clean_team_name(name):
    name = str(name).strip()
    half = len(name) // 2

    if len(name) % 2 == 0 and name[:half] == name[half:]:
        return name[:half]

    return name


# --------------------------------------------------
# SECTION 1: PROCESS THE ORIGINAL 19 STAT TABLES
# --------------------------------------------------

for block_number, start in enumerate(range(0, len(df), 33)):

    # Get the category names from the metadata rows
    category = str(df.iloc[block_number]["TypeA"])
    stat_type = str(df.iloc[block_number]["TypeB"])

    # Read the column headers and 32 team rows
    headers = df.iloc[start, 10:26].tolist()

    block = df.iloc[start + 1:start + 33, 10:26].copy()
    block.columns = headers

    # Clean team names
    block.iloc[:, 0] = block.iloc[:, 0].apply(clean_team_name)

    # Give each statistic a unique name
    new_columns = []

    for i, column in enumerate(block.columns):
        if i == 0:
            new_columns.append("Team")
        else:
            new_columns.append(
                category + "_" + stat_type + "_" + str(column)
            )

    # Make duplicate column names unique
    unique_columns = []
    counts = {}

    for column in new_columns:
        if column not in counts:
            counts[column] = 0
            unique_columns.append(column)
        else:
            counts[column] += 1
            unique_columns.append(
                column + "_" + str(counts[column])
            )

    block.columns = unique_columns

    # Build a table with correctly typed columns
    converted = pd.DataFrame(index=block.index)

    converted["Team"] = (
        block.iloc[:, 0].astype(str).str.strip()
    )

    for i in range(1, len(block.columns)):
        column = block.columns[i]

        # Convert values such as "32T" into 32
        values = (
            block.iloc[:, i]
            .astype(str)
            .str.strip()
            .str.replace(r"T$", "", regex=True)
        )

        converted[column] = pd.to_numeric(
            values,
            errors="coerce"
        )

    team_stats.append(converted)

    print("Processed:", category, stat_type)


# Confirm that category tables were created
print("\nTables created:", len(team_stats))

if len(team_stats) == 0:
    raise ValueError("No category tables were created.")


# --------------------------------------------------
# SECTION 2: COMBINE THE ORIGINAL STAT TABLES
# --------------------------------------------------

rankings = team_stats[0]

for block in team_stats[1:]:
    rankings = rankings.merge(
        block,
        on="Team",
        how="outer"
    )


# --------------------------------------------------
# SECTION 3: READ THE POINTS-ALLOWED TABLE
# --------------------------------------------------

# In your current NFL.xlsx file:
# Column index 27 = full team name
# Column index 28 = total points allowed
# Rows 0 through 31 contain the 32 NFL teams.

points_allowed = pd.DataFrame()

points_allowed["Full_Team"] = (
    df.iloc[0:32, 27].astype(str).str.strip()
)

points_allowed["Points_Allowed"] = pd.to_numeric(
    df.iloc[0:32, 28],
    errors="coerce"
)


# Convert the full team names into the short names
# used in the original stat tables.

team_name_map = {
    "Arizona Cardinals": "Cardinals",
    "Atlanta Falcons": "Falcons",
    "Baltimore Ravens": "Ravens",
    "Buffalo Bills": "Bills",
    "Carolina Panthers": "Panthers",
    "Chicago Bears": "Bears",
    "Cincinnati Bengals": "Bengals",
    "Cleveland Browns": "Browns",
    "Dallas Cowboys": "Cowboys",
    "Denver Broncos": "Broncos",
    "Detroit Lions": "Lions",
    "Green Bay Packers": "Packers",
    "Houston Texans": "Texans",
    "Indianapolis Colts": "Colts",
    "Jacksonville Jaguars": "Jaguars",
    "Kansas City Chiefs": "Chiefs",
    "Las Vegas Raiders": "Raiders",
    "Los Angeles Chargers": "Chargers",
    "Los Angeles Rams": "Rams",
    "Miami Dolphins": "Dolphins",
    "Minnesota Vikings": "Vikings",
    "New England Patriots": "Patriots",
    "New Orleans Saints": "Saints",
    "New York Giants": "Giants",
    "New York Jets": "Jets",
    "Philadelphia Eagles": "Eagles",
    "Pittsburgh Steelers": "Steelers",
    "San Francisco 49ers": "49ers",
    "Seattle Seahawks": "Seahawks",
    "Tampa Bay Buccaneers": "Buccaneers",
    "Tennessee Titans": "Titans",
    "Washington Commanders": "Commanders"
}

points_allowed["Team"] = (
    points_allowed["Full_Team"].map(team_name_map)
)


# Check for missing team names or points-allowed values
if points_allowed["Team"].isna().any():
    missing_teams = points_allowed.loc[
        points_allowed["Team"].isna(), "Full_Team"
    ].tolist()

    raise ValueError(
        "These team names could not be matched: "
        + str(missing_teams)
    )

if points_allowed["Points_Allowed"].isna().any():
    raise ValueError(
        "Some points-allowed values are missing or invalid."
    )


# Keep only the columns needed for the merge
points_allowed = points_allowed[
    ["Team", "Points_Allowed"]
]


# --------------------------------------------------
# SECTION 4: MERGE POINTS ALLOWED INTO THE RANKINGS
# --------------------------------------------------

rankings = rankings.merge(
    points_allowed,
    on="Team",
    how="left"
)


# Verify that every team received a points-allowed value
if rankings["Points_Allowed"].isna().any():
    missing_teams = rankings.loc[
        rankings["Points_Allowed"].isna(), "Team"
    ].tolist()

    raise ValueError(
        "Points allowed missing for: " + str(missing_teams)
    )


# --------------------------------------------------
# SECTION 5: SAVE AND VERIFY THE COMBINED FILE
# --------------------------------------------------

rankings.to_csv("NFL_Combined.csv", index=False)

print("\nTeams found:", rankings["Team"].nunique())
print("Columns:", len(rankings.columns))

print("\nPoints allowed by team:")
print(
    rankings[["Team", "Points_Allowed"]]
    .sort_values("Points_Allowed")
    .to_string(index=False)
)

print("\nSaved NFL_Combined.csv")