# Sports Analytics Project

An NFL power-ranking and game-prediction system built in Python. It pulls team statistics, scores every team on offense, defense and special teams, projects the score and win probability of any matchup, logs those predictions, and retrains itself as real results come in. A Streamlit dashboard displays everything.

## What it does

- **Combines 19 NFL.com team-stat tables** (offense, defense and special teams) plus a points-allowed table into one clean dataset.
- **Ranks all 32 teams** with z-score based Offense, Defense, Special Teams and Overall scores, and saves a weekly snapshot so rankings can be compared over time.
- **Predicts games**: projected score, win probability and upset chance for any home/away pairing.
- **Learns from results**: completed games are logged, and logistic-regression models (win, home blowout, away blowout) are retrained from them.
- **Shows it all in a dashboard**: game cards with logos, model accuracy, power rankings and ranking history.

## How the pipeline fits together

```
NFL.xlsx  ──►  NFL.py  ──►  NFL_Combined.csv  ──►  RankNFL.py  ──►  NFL_Team_Rankings.csv
(Power Query pulls)                                      │                     │
                                                         │                     ▼
                                                         │          NFL_Category_Rankings.py
                                                         │                     │
                                                         ▼                     ▼
                                           NFL_Ranking_History.csv    NFL_Category_Rankings.csv
                                           NFL_Rankings_Report.xlsx            │
                                                                               ▼
                    NFL_Model_Weights.json  ◄──  TrainNFLModel.py      PredictNFL.py ──► NFL_Game_Log.csv
                                                        ▲                                      │
                                                        └──────────  UpdatedNFLModel.py  ◄─────┘
                                                                     (enter final scores)
                                                                               │
                                                                               ▼
                                                                      NFL_Dashboard.py
```

## Files

### Scripts

| File | Purpose |
|---|---|
| `NFL.py` | Reads `NFL.xlsx`, splits it into its 19 stat tables, cleans team names (`"SaintsSaints"` becomes `"Saints"`), converts values such as `"32T"` to numbers, merges everything on team, adds points allowed, and writes `NFL_Combined.csv`. |
| `RankNFL.py` | Asks how many games have been played, estimates points per game from scoring stats, calculates points allowed per game, builds category scores, ranks teams, and saves the rankings, an Excel report and a weekly history snapshot. |
| `NFL_Category_Rankings.py` | Adds separate Offense, Defense and Special Teams ranks and prints each leaderboard. Saves `NFL_Category_Rankings.csv`. |
| `PredictNFL.py` | Prompts for a home and away team, projects the score and win probability, and appends the prediction to `NFL_Game_Log.csv`. |
| `UpdatedNFLModel.py` | Records the actual final score for a logged prediction by Game ID and prints model accuracy (score error, winner accuracy, Brier score). |
| `TrainNFLModel.py` | Trains the win and blowout models from completed games and writes `NFL_Model_Weights.json`. |
| `NFL_Matchup_History.py` | Shared helpers: division and conference lookups, head-to-head record, head-to-head streak and away-team stadium history. |
| `NFL_Dashboard.py` | Streamlit dashboard. |

### Data files

| File | Contents |
|---|---|
| `NFL.xlsx` / `NFL.csv` | Raw stats pulled from NFL.com with Power Query: 19 tables stacked in 33-row blocks, plus the points-allowed table. |
| `NFL_Combined.csv` | One row per team with every merged statistic and `Points_Allowed`. |
| `NFL_Team_Rankings.csv` | Scores and overall rank for each team. |
| `NFL_Category_Rankings.csv` | The above plus Offense, Defense and Special Teams ranks. This is what `PredictNFL.py` reads. |
| `NFL_Ranking_History.csv` | Weekly ranking snapshots (2022 to 2025 week 18, and 2026 weeks 5 to 9 so far). |
| `NFL_Rankings_Report.xlsx` | Excel report with the top 5 offenses, defenses and special teams, and all 32 teams. |
| `NFL_Game_Log.csv` | Every saved prediction and, once entered, its actual result. |
| `NFL_Model_Weights.json` | Trained model weights (currently trained on 133 completed games from the 2026 season). |
| `NFL_Historical_Games.csv` | *Optional.* Past results used for head-to-head history and extra training data. Columns: `Season, Week, Home_Team, Away_Team, Home_Score, Away_Score`. |
| `NFL_LOGO/` | *Optional.* Team logo images for the dashboard (see below). |

## How the rankings work

Every statistic is standardized into a z-score across the 32 teams, and statistics where lower is better (turnovers, sacks allowed, penalties, defensive yards and touchdowns allowed) are flipped so that higher is always better.

| Score | Built from |
|---|---|
| **Offense** | 60% general offensive stats, 40% estimated points per game |
| **Defense** | 60% general defensive stats, 40% actual points allowed per game |
| **Special Teams** | 35% field-goal %, 25% punt average, 25% average return yards, 15% extra points per game |
| **Overall** | 50% Offense, 40% Defense, 10% Special Teams |

Points per game are estimated from touchdowns, extra points, field goals, two-point conversions, defensive and return touchdowns and safeties. Points allowed per game come from the actual points-allowed table.

## How the predictions work

For each matchup, `PredictNFL.py`:

1. Projects each team's score by blending its scoring average with the opponent's points allowed, then adds a home-field edge and a rating adjustment.
2. Builds ten features: rank advantage, points-per-game difference, defense difference, overall-score difference, same division, same conference, head-to-head win rate, head-to-head streak, home-venue win rate and away-team stadium streak.
3. Estimates win probability with the first available of:
   - the trained model in `NFL_Model_Weights.json`,
   - a model fit from the game log (needs at least 20 completed games),
   - a starting formula based on the projected point margin.
4. Keeps the model's confidence but makes sure the favorite agrees with the projected score.
5. Saves the prediction and the exact inputs to `NFL_Game_Log.csv`.

`TrainNFLModel.py` fits separate logistic models for home win, home blowout and away blowout (a margin of 14 or more), weights recent seasons more heavily (decay of 0.85 per season) and needs at least 30 usable games.

> **Note:** the Brier score printed during training is measured on the same games the model was trained on, so it is a basic diagnostic and not a test-set result. The dashboard's Model Performance tab measures how the saved predictions did against real results.

## Setup

Requires Python 3.9 or newer.

```bash
git clone https://github.com/LiamCB123/SportsAnalyticsProject.git
cd SportsAnalyticsProject
pip install pandas openpyxl streamlit
```

Keep all scripts and CSV files in the same folder, since they read each other by filename.

## Usage

Run these from the project folder.

**1. Refresh the data.** Open `NFL.xlsx`, choose **Data → Refresh All**, and save. Then build the combined file:

```bash
python NFL.py
```

**2. Rank the teams.** Enter the number of games played, then the season and week to save a snapshot:

```bash
python RankNFL.py
python NFL_Category_Rankings.py
```

**3. Predict a game.**

```bash
python PredictNFL.py
```

**4. After the game is played,** enter the final score using the Game ID that was printed:

```bash
python UpdatedNFLModel.py
```

**5. Retrain the model** once there are enough completed games:

```bash
python TrainNFLModel.py
```

**6. Open the dashboard.**

```bash
streamlit run NFL_Dashboard.py
```

The dashboard has four tabs: Game Predictions, Model Performance, Power Rankings and Ranking History. To show team logos, put images in a folder named `NFL_LOGO` beside the dashboard, named by nickname (`Bills.png`), abbreviation (`BUF.png`) or full name.

## Data notes

- Team names must match across files (for example `Bills`, `49ers`, `Commanders`).
- In the Power Query that pulls NFL.com, load every column as **text**. Some columns mix numbers and text (`PDef`, `FC`, `Ret`, and values such as `68T`), and forcing them to whole numbers turns the text into errors that show up as blanks after a refresh. `NFL.py` does the number conversion afterward.
- NFL.com shows each team name twice in one cell; `NFL.py` collapses it to one copy.
- Leave room for the main query table (columns H to Z in `NFL.xlsx`) so the points-allowed table does not sit in its way.

## Limitations

- Statistics are season-to-date totals, so rankings are not adjusted for strength of schedule.
- Early-season rankings rest on few games and move a lot from week to week.
- With a small number of completed games, the trained model can be unstable. Treat probabilities as estimates, not guarantees.

## Roadmap ideas

- Opponent-adjusted statistics.
- Out-of-sample validation (train on earlier weeks, test on later ones).
- Injury and rest-day features.
- Automated weekly data refresh.
