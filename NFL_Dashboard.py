
import os
import re
import base64
from pathlib import Path


import pandas as pd
import streamlit as st

# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

LOG_FILE = BASE_DIR / "NFL_Game_Log.csv"
LOGO_FOLDER = BASE_DIR / "NFL_LOGO"
RANKINGS_FILE = BASE_DIR / "NFL_Team_Rankings.csv"
RANKING_HISTORY_FILE = BASE_DIR / "NFL_Ranking_History.csv"

st.set_page_config(
    page_title="NFL Analytics Dashboard",
    page_icon="🏈",
    layout="wide"
)

# NFL team abbreviations and aliases
TEAM_LOGOS = {
    "49ers": ["SF", "49ers"],
    "Bears": ["CHI", "Bears"],
    "Bengals": ["CIN", "Bengals"],
    "Bills": ["BUF", "Bills"],
    "Broncos": ["DEN", "Broncos"],
    "Browns": ["CLE", "Browns"],
    "Buccaneers": ["TB", "Buccaneers"],
    "Cardinals": ["ARI", "Cardinals"],
    "Chargers": ["LAC", "Chargers"],
    "Chiefs": ["KC", "Chiefs"],
    "Colts": ["IND", "Colts"],
    "Commanders": ["WSH", "WAS", "Commanders"],
    "Cowboys": ["DAL", "Cowboys"],
    "Dolphins": ["MIA", "Dolphins"],
    "Eagles": ["PHI", "Eagles"],
    "Falcons": ["ATL", "Falcons"],
    "Giants": ["NYG", "Giants"],
    "Jaguars": ["JAX", "JAC", "Jaguars"],
    "Jets": ["NYJ", "Jets"],
    "Lions": ["DET", "Lions"],
    "Packers": ["GB", "Packers"],
    "Panthers": ["CAR", "Panthers"],
    "Patriots": ["NE", "Patriots"],
    "Raiders": ["LV", "OAK", "Raiders"],
    "Rams": ["LAR", "LA", "Rams"],
    "Ravens": ["BAL", "Ravens"],
    "Saints": ["NO", "Saints"],
    "Seahawks": ["SEA", "Seahawks"],
    "Steelers": ["PIT", "Steelers"],
    "Texans": ["HOU", "Texans"],
    "Titans": ["TEN", "Titans"],
    "Vikings": ["MIN", "Vikings"]
}

# --------------------------------------------------
# DASHBOARD DESIGN
# --------------------------------------------------

st.html("""
<style>

.stApp {
    background-color: #101418;
    color: white;
}

.block-container {
    max-width: 1150px;
    padding-top: 2rem;
}

h1 {
    text-align: center;
    font-weight: 900;
    letter-spacing: 2px;
}

.subtitle {
    text-align: center;
    color: #aab3bd;
    margin-bottom: 25px;
    font-size: 13px;
    letter-spacing: 1px;
}

.game-card {
    background: #1b2229;
    border: 1px solid #343d46;
    border-radius: 12px;
    padding: 22px;
    margin: 15px auto;
    max-width: 1000px;
}

.game-status {
    text-align: center;
    color: #aab3bd;
    font-size: 12px;
    font-weight: bold;
    letter-spacing: 2px;
    margin-bottom: 18px;
}

.matchup {
    display: grid;
    grid-template-columns: 1fr 130px 1fr;
    align-items: center;
    gap: 10px;
}

.team {
    display: flex;
    align-items: center;
    gap: 15px;
    min-width: 0;
}

.team.home {
    flex-direction: row-reverse;
    text-align: right;
}

.team img {
    width: 80px;
    height: 80px;
    object-fit: contain;
}

.team-name {
    font-size: 18px;
    font-weight: 800;
}

.probability {
    font-size: 32px;
    font-weight: 900;
    margin-top: 4px;
}

.favorite {
    color: #45d48a;
}

.underdog {
    color: #ff7070;
}

.center {
    text-align: center;
}

.at {
    font-size: 20px;
    font-weight: bold;
    color: #aab3bd;
}

.score-label {
    color: #aab3bd;
    font-size: 10px;
    letter-spacing: 1px;
    margin-top: 8px;
}

.score {
    font-size: 25px;
    font-weight: 900;
    white-space: nowrap;
}

.bar {
    display: flex;
    width: 100%;
    height: 14px;
    border-radius: 20px;
    overflow: hidden;
    margin-top: 22px;
}

.bar-away {
    background: #d9535d;
}

.bar-home {
    background: #24a66a;
}

.bar-labels {
    display: flex;
    justify-content: space-between;
    color: #c5cbd2;
    font-size: 12px;
    margin-top: 6px;
}

.details {
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
    border-top: 1px solid #343d46;
    margin-top: 15px;
    padding-top: 12px;
}

.upset {
    color: #f4c66a;
    font-weight: bold;
}

.muted {
    color: #aab3bd;
    font-size: 12px;
}

@media (max-width: 650px) {
    .matchup {
        grid-template-columns: 1fr 75px 1fr;
        gap: 4px;
    }

    .team {
        flex-direction: column;
        text-align: center;
        gap: 5px;
    }

    .team.home {
        flex-direction: column;
        text-align: center;
    }

    .team img {
        width: 55px;
        height: 55px;
    }

    .team-name {
        font-size: 13px;
    }

    .probability {
        font-size: 23px;
    }

    .score {
        font-size: 18px;
    }
}


.ranking-board {
    display: grid;
    grid-auto-flow: column;
    grid-template-rows: repeat(8, minmax(66px, auto));
    grid-auto-columns: minmax(0, 1fr);
    gap: 10px 18px;
    margin: 18px 0 28px 0;
}
.ranking-tile {
    display: grid;
    grid-template-columns: 42px minmax(0, 1fr);
    min-height: 66px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.16);
    background: linear-gradient(110deg, #26313d, #111923);
    box-shadow: 0 4px 10px rgba(0,0,0,0.35);
}
.ranking-number {
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(90deg, #f5f5f5, #bfc4c9);
    color: #15191e;
    font-size: 25px;
    font-weight: 950;
}
.ranking-team-panel {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 0;
    padding: 5px 12px;
    background: linear-gradient(115deg, #174d80, #102b48);
}
.ranking-team-name {
    color: white;
    font-size: 14px;
    font-weight: 850;
    text-align: center;
    letter-spacing: 0.5px;
    text-shadow: 0 2px 4px rgba(0,0,0,0.7);
}
.ranking-logo {
    display: block;
    width: 100%;
    max-width: 145px;
    height: 54px;
    object-fit: contain;
    filter: drop-shadow(0 2px 2px rgba(0,0,0,0.35));
}
.ranking-logo.missing-logo {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 54px;
    height: 54px;
    border: 1px dashed rgba(255,255,255,0.55);
    border-radius: 50%;
    color: white;
    font-weight: 900;
    font-size: 13px;
}
.ranking-board-caption {
    color: #aab3bd;
    font-size: 12px;
    margin-top: -8px;
    margin-bottom: 12px;
}
@media (max-width: 900px) {
    .ranking-board {
        grid-auto-flow: row;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        grid-template-rows: none;
    }
}
@media (max-width: 560px) {
    .ranking-board {
        grid-template-columns: 1fr;
    }
}


.history-ranking-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px 14px;margin:12px 0 20px}
.history-ranking-card{display:grid;grid-template-columns:38px minmax(0,1fr);min-height:62px;overflow:hidden;border:1px solid rgba(255,255,255,.15);background:linear-gradient(110deg,#26313d,#111923);box-shadow:0 3px 8px rgba(0,0,0,.3)}
.history-ranking-number{display:flex;align-items:center;justify-content:center;background:linear-gradient(90deg,#f5f5f5,#bfc4c9);color:#15191e;font-size:23px;font-weight:950}
.history-ranking-team{display:flex;align-items:center;justify-content:center;min-width:0;padding:4px 8px;background:linear-gradient(115deg,#174d80,#102b48)}
.history-ranking-team .ranking-logo{width:100%;max-width:125px;height:48px}
@media(max-width:900px){.history-ranking-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.history-ranking-grid{grid-template-columns:1fr}}

</style>
""")

st.markdown("# NFL GAME PROBABILITIES", unsafe_allow_html=True)

st.markdown("""
<div class="subtitle">
TEAM WIN PROBABILITIES · POTENTIAL UPSETS · PROJECTED SCORES
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# LOGO FUNCTIONS
# --------------------------------------------------


def normalize(name):
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


# Full team names used to match logo files named with either a city or nickname.
TEAM_FULL_NAMES = {
    "49ers": "San Francisco 49ers",
    "Bears": "Chicago Bears",
    "Bengals": "Cincinnati Bengals",
    "Bills": "Buffalo Bills",
    "Broncos": "Denver Broncos",
    "Browns": "Cleveland Browns",
    "Buccaneers": "Tampa Bay Buccaneers",
    "Cardinals": "Arizona Cardinals",
    "Chargers": "Los Angeles Chargers",
    "Chiefs": "Kansas City Chiefs",
    "Colts": "Indianapolis Colts",
    "Commanders": "Washington Commanders",
    "Cowboys": "Dallas Cowboys",
    "Dolphins": "Miami Dolphins",
    "Eagles": "Philadelphia Eagles",
    "Falcons": "Atlanta Falcons",
    "Giants": "New York Giants",
    "Jaguars": "Jacksonville Jaguars",
    "Jets": "New York Jets",
    "Lions": "Detroit Lions",
    "Packers": "Green Bay Packers",
    "Panthers": "Carolina Panthers",
    "Patriots": "New England Patriots",
    "Raiders": "Las Vegas Raiders",
    "Rams": "Los Angeles Rams",
    "Ravens": "Baltimore Ravens",
    "Saints": "New Orleans Saints",
    "Seahawks": "Seattle Seahawks",
    "Steelers": "Pittsburgh Steelers",
    "Texans": "Houston Texans",
    "Titans": "Tennessee Titans",
    "Vikings": "Minnesota Vikings"
}


def find_logo(team):
    folder = Path(LOGO_FOLDER)

    if not folder.is_dir():
        return None

    team_text = str(team).strip()
    team_key = normalize(team_text)
    candidates = [team_text]

    # Resolve nickname, abbreviation, or full team name to the canonical team.
    for nickname, aliases in TEAM_LOGOS.items():
        full_name = TEAM_FULL_NAMES.get(nickname, "")
        accepted = [nickname, full_name] + aliases

        if any(normalize(value) == team_key for value in accepted):
            candidates.extend(accepted)
            break

        # Also accept a full team name when the supplied value contains it.
        if full_name and team_key in [normalize(full_name)]:
            candidates.extend(accepted)
            break

    candidate_names = [normalize(value) for value in candidates if value]

    for file in folder.iterdir():
        if file.suffix.lower() not in [".png", ".jpg", ".jpeg", ".webp"]:
            continue

        file_name = normalize(file.stem)

        # Exact match first; then allow filenames such as "buffalo_bills_logo".
        if file_name in candidate_names:
            return file

        for candidate in candidate_names:
            if candidate and (
                file_name.startswith(candidate)
                or candidate.startswith(file_name)
            ):
                return file

    return None


def get_logo_html(team):
    logo_path = find_logo(team)

    if logo_path is None:
        return (
            '<div class="ranking-logo missing-logo">'
            + str(team)[:3].upper()
            + '</div>'
        )

    with open(logo_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")

    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp"
    }
    mime = mime_types.get(logo_path.suffix.lower(), "image/png")

    return (
        f'<img class="ranking-logo" src="data:{mime};base64,{encoded}" '
        f'alt="{team} logo">'
    )


# --------------------------------------------------
# PROBABILITY FUNCTIONS
# --------------------------------------------------

def get_probability(row, column):

    value = pd.to_numeric(
        row.get(column),
        errors="coerce"
    )

    if pd.isna(value):
        return None

    value = float(value)

    # Convert percentages to decimals if needed
    if value > 1:
        value = value / 100

    return max(0, min(1, value))


def get_upset_probability(row):

    saved = get_probability(
        row,
        "Predicted_Upset_Probability"
    )

    if saved is not None:
        return saved

    home = get_probability(
        row,
        "Predicted_Home_Win_Probability"
    )

    away = get_probability(
        row,
        "Predicted_Away_Win_Probability"
    )

    if home is None or away is None:
        return None

    return min(home, away)


# --------------------------------------------------
# LOAD GAME DATA
# --------------------------------------------------

if not os.path.exists(LOG_FILE):
    st.error("NFL_Game_Log.csv could not be found.")
    st.stop()

games = pd.read_csv(LOG_FILE)

required_columns = [
    "Home_Team",
    "Away_Team",
    "Predicted_Home_Score",
    "Predicted_Away_Score",
    "Predicted_Home_Win_Probability",
    "Predicted_Away_Win_Probability"
]

missing = [
    column for column in required_columns
    if column not in games.columns
]

if missing:
    st.error("Missing columns: " + ", ".join(missing))
    st.stop()


# --------------------------------------------------
# FILTERS
# --------------------------------------------------

if "Completed" in games.columns:

    completed = games["Completed"].astype(str).str.lower().isin(
        ["true", "1", "yes"]
    )

    games["Status"] = completed.map({
        True: "Completed",
        False: "Upcoming"
    })

else:
    games["Status"] = "Upcoming"


with st.sidebar:

    st.header("Dashboard Filters")

    status_filter = st.selectbox(
        "Games",
        ["Upcoming", "Completed", "All"]
    )

    sort_filter = st.selectbox(
        "Sort Matchups",
        [
            "Original Order",
            "Highest Upset Chance",
            "Closest Matchup",
            "Biggest Favorite"
        ]
    )

    teams = sorted(
        set(games["Home_Team"].dropna().astype(str)) |
        set(games["Away_Team"].dropna().astype(str))
    )

    team_filter = st.selectbox(
        "Filter by Team",
        ["All Teams"] + teams
    )


view = games.copy()

if status_filter != "All":
    view = view[view["Status"] == status_filter]

if team_filter != "All Teams":
    view = view[
        (view["Home_Team"] == team_filter) |
        (view["Away_Team"] == team_filter)
    ]


# --------------------------------------------------
# SORT MATCHUPS
# --------------------------------------------------

if sort_filter == "Highest Upset Chance":

    view["_sort"] = view.apply(
        lambda row: get_upset_probability(row) or 0,
        axis=1
    )

    view = view.sort_values("_sort", ascending=False)

elif sort_filter == "Closest Matchup":

    view["_sort"] = view.apply(
        lambda row: abs(
            (get_probability(
                row, "Predicted_Home_Win_Probability"
            ) or 0.5)
            -
            (get_probability(
                row, "Predicted_Away_Win_Probability"
            ) or 0.5)
        ),
        axis=1
    )

    view = view.sort_values("_sort")

elif sort_filter == "Biggest Favorite":

    view["_sort"] = view.apply(
        lambda row: max(
            get_probability(
                row, "Predicted_Home_Win_Probability"
            ) or 0.5,
            get_probability(
                row, "Predicted_Away_Win_Probability"
            ) or 0.5
        ),
        axis=1
    )

    view = view.sort_values("_sort", ascending=False)


# --------------------------------------------------
# DASHBOARD TABS
# --------------------------------------------------

games_tab, performance_tab, rankings_tab, history_tab = st.tabs(
    ["🏈 Game Predictions", "🎯 Model Performance", "📊 Power Rankings", "📈 Ranking History"]
)


# --------------------------------------------------
# GAME PREDICTIONS
# --------------------------------------------------

with games_tab:

    st.caption(f"{len(view)} MATCHUPS DISPLAYED")

    for _, game in view.iterrows():

        home = str(game["Home_Team"])
        away = str(game["Away_Team"])

        home_prob = get_probability(
            game, "Predicted_Home_Win_Probability"
        )
        away_prob = get_probability(
            game, "Predicted_Away_Win_Probability"
        )

        if home_prob is None or away_prob is None:
            continue

        home_favorite = home_prob >= away_prob

        if home_favorite:
            underdog = away
            favorite = home
            home_class = "favorite"
            away_class = "underdog"
        else:
            underdog = home
            favorite = away
            home_class = "underdog"
            away_class = "favorite"

        upset = get_upset_probability(game)
        saved_underdog = game.get("Predicted_Underdog")

        if pd.notna(saved_underdog) and str(saved_underdog).strip():
            underdog = str(saved_underdog).strip()

        home_score = pd.to_numeric(
            game["Predicted_Home_Score"], errors="coerce"
        )
        away_score = pd.to_numeric(
            game["Predicted_Away_Score"], errors="coerce"
        )

        if pd.notna(home_score) and pd.notna(away_score):
            score = f"{away_score:.0f} – {home_score:.0f}"
            predicted_margin = home_score - away_score
        else:
            score = "—"
            predicted_margin = None

        is_completed = str(game.get("Completed", "")).lower() in [
            "true", "1", "yes"
        ]

        actual_home = pd.to_numeric(
            game.get("Actual_Home_Score"), errors="coerce"
        )
        actual_away = pd.to_numeric(
            game.get("Actual_Away_Score"), errors="coerce"
        )

        actual_section = ""

        if is_completed and pd.notna(actual_home) and pd.notna(actual_away):
            actual_margin = actual_home - actual_away
            home_point_diff = actual_home - home_score if pd.notna(home_score) else None
            away_point_diff = actual_away - away_score if pd.notna(away_score) else None

            if predicted_margin is not None:
                margin_error = abs(actual_margin - predicted_margin)
                predicted_margin_text = (
                    f"{'Home' if predicted_margin > 0 else 'Away' if predicted_margin < 0 else 'Tie'} "
                    f"by {abs(predicted_margin):.1f}"
                )
                actual_margin_text = (
                    f"{'Home' if actual_margin > 0 else 'Away' if actual_margin < 0 else 'Tie'} "
                    f"by {abs(actual_margin):.0f}"
                )
            else:
                margin_error = None
                predicted_margin_text = "—"
                actual_margin_text = "—"

            home_diff_text = f"{home_point_diff:+.1f}" if home_point_diff is not None else "—"
            away_diff_text = f"{away_point_diff:+.1f}" if away_point_diff is not None else "—"
            margin_error_text = f"{margin_error:.1f} pts" if margin_error is not None else "—"

            predicted_winner = home if home_prob >= away_prob else away
            actual_winner = home if actual_home > actual_away else away if actual_away > actual_home else "Tie"
            pick_result = "CORRECT PICK" if predicted_winner == actual_winner else "INCORRECT PICK"
            actual_section = f"""
            <div class="details">
                <span><b>ACTUAL SCORE:</b> {away} {actual_away:.0f} – {home} {actual_home:.0f}</span>
                <span><b>PREDICTED WINNER:</b> {predicted_winner}</span>
                <span><b>ACTUAL WINNER:</b> {actual_winner}</span>
                <span><b>{pick_result}</b></span>
            </div>
            <div class="details">
                <span><b>{home} point difference:</b> {home_diff_text}</span>
                <span><b>{away} point difference:</b> {away_diff_text}</span>
                <span><b>Predicted margin:</b> {predicted_margin_text}</span>
                <span><b>Actual margin:</b> {actual_margin_text}</span>
                <span><b>Margin error:</b> {margin_error_text}</span>
            </div>
            """

        upset_text = (
            f"Potential Upset: {upset:.1%} | Underdog: {underdog}"
            if upset is not None
            else "Potential Upset: unavailable"
        )

        html = f"""
        <div class="game-card">
            <div class="game-status">
                {str(game['Status']).upper()} MATCHUP
            </div>
            <div class="matchup">
                <div class="team">
                    {get_logo_html(away)}
                    <div>
                        <div class="team-name">{away}</div>
                        <div class="probability {away_class}">{away_prob:.1%}</div>
                        <div class="muted">WIN PROBABILITY</div>
                    </div>
                </div>
                <div class="center">
                    <div class="at">@</div>
                    <div class="score-label">PROJECTED SCORE</div>
                    <div class="score">{score}</div>
                </div>
                <div class="team home">
                    {get_logo_html(home)}
                    <div>
                        <div class="team-name">{home}</div>
                        <div class="probability {home_class}">{home_prob:.1%}</div>
                        <div class="muted">WIN PROBABILITY</div>
                    </div>
                </div>
            </div>
            <div class="bar">
                <div style="width:{away_prob * 100}%; background:{'#24a66a' if not home_favorite else '#d9535d'};"></div>
                <div style="width:{home_prob * 100}%; background:{'#24a66a' if home_favorite else '#d9535d'};"></div>
            </div>
            <div class="bar-labels">
                <span>{away} {away_prob:.1%}</span>
                <span>{home} {home_prob:.1%}</span>
            </div>
            <div class="details">
                <span class="upset">{upset_text}</span>
                <span class="muted">{favorite} projected favorite</span>
            </div>
            {actual_section}
        </div>
        """
        st.html(html)

    if view.empty:
        st.info("No games match your selected filters.")


# --------------------------------------------------
# MODEL PERFORMANCE
# --------------------------------------------------

with performance_tab:
    st.subheader("Model Performance")
    st.caption(
        "Performance is calculated from completed games that have actual scores and valid model predictions. "
        "A predicted winner is the team with the higher saved win probability."
    )

    perf = games.copy()
    for col in [
        "Predicted_Home_Score", "Predicted_Away_Score",
        "Actual_Home_Score", "Actual_Away_Score",
        "Predicted_Home_Win_Probability", "Predicted_Away_Win_Probability"
    ]:
        perf[col] = pd.to_numeric(perf[col], errors="coerce")

    completed_mask = perf.get("Completed", pd.Series(False, index=perf.index)).astype(str).str.lower().isin(["true", "1", "yes"])
    valid = perf[
        completed_mask
        & perf["Predicted_Home_Score"].notna()
        & perf["Predicted_Away_Score"].notna()
        & perf["Actual_Home_Score"].notna()
        & perf["Actual_Away_Score"].notna()
        & perf["Predicted_Home_Win_Probability"].notna()
        & perf["Predicted_Away_Win_Probability"].notna()
    ].copy()

    if valid.empty:
        st.info("There are no completed games with all required prediction and actual-score fields yet.")
    else:
        valid["Predicted_Winner"] = valid.apply(
            lambda r: r["Home_Team"] if r["Predicted_Home_Win_Probability"] >= r["Predicted_Away_Win_Probability"] else r["Away_Team"], axis=1
        )
        valid["Actual_Winner_Calc"] = valid.apply(
            lambda r: r["Home_Team"] if r["Actual_Home_Score"] > r["Actual_Away_Score"] else r["Away_Team"] if r["Actual_Away_Score"] > r["Actual_Home_Score"] else "Tie", axis=1
        )
        valid["Pick_Correct"] = valid["Predicted_Winner"] == valid["Actual_Winner_Calc"]
        valid["Home_Score_Error"] = (valid["Predicted_Home_Score"] - valid["Actual_Home_Score"]).abs()
        valid["Away_Score_Error"] = (valid["Predicted_Away_Score"] - valid["Actual_Away_Score"]).abs()
        valid["Total_Score_Error"] = (valid["Home_Score_Error"] + valid["Away_Score_Error"]) / 2
        valid["Predicted_Margin"] = valid["Predicted_Home_Score"] - valid["Predicted_Away_Score"]
        valid["Actual_Margin"] = valid["Actual_Home_Score"] - valid["Actual_Away_Score"]
        valid["Margin_Error"] = (valid["Predicted_Margin"] - valid["Actual_Margin"]).abs()
        valid["Favorite_Probability"] = valid[["Predicted_Home_Win_Probability", "Predicted_Away_Win_Probability"]].max(axis=1)
        valid["Brier_Score"] = valid.apply(
            lambda r: (r["Predicted_Home_Win_Probability"] - (1 if r["Actual_Winner_Calc"] == r["Home_Team"] else 0)) ** 2
                    + (r["Predicted_Away_Win_Probability"] - (1 if r["Actual_Winner_Calc"] == r["Away_Team"] else 0)) ** 2,
            axis=1
        ) / 2

        total = len(valid)
        wins = int(valid["Pick_Correct"].sum())
        losses = total - wins
        accuracy = wins / total
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Model Record", f"{wins}-{losses}")
        c2.metric("Winner Accuracy", f"{accuracy:.1%}")
        c3.metric("Avg. Score Error", f"{valid['Total_Score_Error'].mean():.2f} pts")
        c4.metric("Avg. Margin Error", f"{valid['Margin_Error'].mean():.2f} pts")
        c5.metric("Brier Score", f"{valid['Brier_Score'].mean():.3f}", help="Lower is better; measures probability accuracy, not just winner picks.")

        st.markdown("#### Prediction vs. Actual Scores")
        score_summary = pd.DataFrame({
            "Measure": ["Home team score", "Away team score"],
            "Average predicted": [valid["Predicted_Home_Score"].mean(), valid["Predicted_Away_Score"].mean()],
            "Average actual": [valid["Actual_Home_Score"].mean(), valid["Actual_Away_Score"].mean()],
            "Mean absolute error": [valid["Home_Score_Error"].mean(), valid["Away_Score_Error"].mean()]
        }).round(2)
        st.dataframe(score_summary, use_container_width=True, hide_index=True)

        st.markdown("#### Accuracy by Confidence")
        confidence_bins = [0.50, 0.55, 0.60, 0.65, 0.70, 0.80, 1.001]
        confidence_labels = ["50–54%", "55–59%", "60–64%", "65–69%", "70–79%", "80–100%"]
        valid["Confidence_Band"] = pd.cut(valid["Favorite_Probability"], bins=confidence_bins, labels=confidence_labels, right=False)
        confidence = valid.groupby("Confidence_Band", observed=False).agg(
            Games=("Pick_Correct", "size"), Correct=("Pick_Correct", "sum"), Accuracy=("Pick_Correct", "mean")
        ).reset_index()
        confidence["Accuracy"] = (confidence["Accuracy"] * 100).round(1)
        st.dataframe(confidence.rename(columns={"Confidence_Band": "Favorite win probability", "Accuracy": "Accuracy (%)"}), use_container_width=True, hide_index=True)

        st.markdown("#### Teams the Model Predicts Best")
        team_rows = []
        for team in sorted(set(valid["Home_Team"].dropna().astype(str)) | set(valid["Away_Team"].dropna().astype(str))):
            picked = valid[valid["Predicted_Winner"] == team]
            if picked.empty:
                continue
            correct = int((picked["Actual_Winner_Calc"] == team).sum())
            team_rows.append({"Team": team, "Times picked to win": len(picked), "Correct picks": correct,
                              "Incorrect picks": len(picked) - correct, "Pick accuracy (%)": round(100 * correct / len(picked), 1),
                              "Avg. predicted score error": round(pd.concat([
                                  valid.loc[valid["Home_Team"] == team, "Home_Score_Error"],
                                  valid.loc[valid["Away_Team"] == team, "Away_Score_Error"]
                              ]).mean(), 2)})
        team_accuracy = pd.DataFrame(team_rows)
        if not team_accuracy.empty:
            min_sample = st.slider("Minimum times picked to include a team", 1, max(1, int(team_accuracy["Times picked to win"].max())), 3, key="team_accuracy_min")
            filtered_team_accuracy = team_accuracy[team_accuracy["Times picked to win"] >= min_sample].sort_values(
                ["Pick accuracy (%)", "Times picked to win"], ascending=[False, False]
            )
            st.dataframe(filtered_team_accuracy, use_container_width=True, hide_index=True)
            st.caption("Team accuracy measures games where the model selected that team as the winner. The sample-size filter helps avoid overrating teams with very few picks.")

        st.markdown("#### Completed Game Results")
        results = valid[["Home_Team", "Away_Team", "Predicted_Winner", "Actual_Winner_Calc",
                         "Predicted_Away_Score", "Predicted_Home_Score", "Actual_Away_Score", "Actual_Home_Score",
                         "Total_Score_Error", "Margin_Error", "Favorite_Probability", "Pick_Correct"]].copy()
        results = results.rename(columns={
            "Home_Team": "Home", "Away_Team": "Away", "Predicted_Winner": "Predicted winner",
            "Actual_Winner_Calc": "Actual winner", "Predicted_Away_Score": "Pred. away",
            "Predicted_Home_Score": "Pred. home", "Actual_Away_Score": "Actual away",
            "Actual_Home_Score": "Actual home", "Total_Score_Error": "Avg. score error (pts)",
            "Margin_Error": "Margin error (pts)", "Favorite_Probability": "Favorite probability",
            "Pick_Correct": "Correct pick"
        })
        for col in ["Pred. away", "Pred. home", "Actual away", "Actual home", "Avg. score error (pts)", "Margin error (pts)"]:
            results[col] = results[col].round(1)
        results["Favorite probability"] = (results["Favorite probability"] * 100).round(1).astype(str) + "%"
        st.dataframe(results.sort_values("Correct pick", ascending=True), use_container_width=True, hide_index=True)


# --------------------------------------------------
# POWER RANKINGS
# --------------------------------------------------

def show_ranking_table(data, rank_column, score_column, title):
    st.subheader(title)

    if "Team" not in data.columns or score_column not in data.columns:
        st.warning(f"{title} data is not available in the rankings CSV.")
        return

    display = data[["Team", score_column]].copy()
    display[score_column] = pd.to_numeric(
        display[score_column], errors="coerce"
    )

    if rank_column in data.columns:
        display["Rank"] = pd.to_numeric(
            data[rank_column], errors="coerce"
        )
        display = display.sort_values("Rank", na_position="last")
    else:
        display = display.sort_values(
            score_column, ascending=False, na_position="last"
        )
        display.insert(0, "Rank", range(1, len(display) + 1))

    display = display.dropna(subset=["Team"]).reset_index(drop=True)

    tiles = []
    for _, team_row in display.iterrows():
        team_name = str(team_row["Team"])
        rank_value = team_row["Rank"]
        rank_text = str(int(rank_value)) if pd.notna(rank_value) else "—"
        logo = get_logo_html(team_name)

        tiles.append(f"""
            <div class="ranking-tile">
                <div class="ranking-number">{rank_text}</div>
                <div class="ranking-team-panel">
                    {logo}
                </div>
            </div>
        """)

    board_html = f"""
        <div class="ranking-board">
            {''.join(tiles)}
        </div>
        <div class="ranking-board-caption">
            Teams are ordered from highest-ranked to lowest-ranked.
            Logo files are loaded from the NFL_LOGO folder.
        </div>
    """
    st.html(board_html)

    # Keep the numeric ratings available below the visual board.
    with st.expander("View ranking scores"):
        score_display = display[["Rank", "Team", score_column]].copy()
        score_display = score_display.rename(
            columns={score_column: "Rating"}
        )
        score_display["Rating"] = score_display["Rating"].round(3)
        st.dataframe(
            score_display,
            use_container_width=True,
            hide_index=True
        )


with rankings_tab:

    if not RANKINGS_FILE.exists():
        st.warning("NFL_Team_Rankings.csv was not found beside the dashboard file.")
    else:
        rankings = pd.read_csv(RANKINGS_FILE)

        if "Team" not in rankings.columns:
            st.error("The rankings file needs a 'Team' column.")
        else:
            ranking_options = {
                "Overall Power Rankings": ("Rank", "Overall_Score"),
                "Offensive Power Rankings": ("Offense_Rank", "Offense_Score"),
                "Defensive Power Rankings": ("Defense_Rank", "Defense_Score"),
                "Special Teams Rankings": ("Special_Teams_Rank", "Special_Teams_Score")
            }

            selected_ranking = st.selectbox(
                "Choose Ranking",
                list(ranking_options.keys())
            )

            st.caption("These are the current rankings from NFL_Team_Rankings.csv. Update that file with your latest weekly stats and the dashboard will display the refreshed rankings; historical weekly snapshots remain separate.")
            rank_col, score_col = ranking_options[selected_ranking]
            show_ranking_table(rankings, rank_col, score_col, selected_ranking)

            st.subheader("Team Rating Comparison")
            team_names = sorted(rankings["Team"].dropna().astype(str).unique())
            selected_teams = st.multiselect(
                "Compare teams",
                team_names,
                default=team_names[:2] if len(team_names) >= 2 else team_names
            )

            if selected_teams:
                comparison_columns = [
                    column for column in [
                        "Team", "Rank", "Overall_Score",
                        "Offense_Rank", "Offense_Score",
                        "Defense_Rank", "Defense_Score",
                        "Special_Teams_Rank", "Special_Teams_Score",
                        "Points_Per_Game", "PAPG"
                    ]
                    if column in rankings.columns
                ]
                comparison = rankings[
                    rankings["Team"].astype(str).isin(selected_teams)
                ][comparison_columns].copy()
                comparison["Logo"] = comparison["Team"].apply(
                    lambda team: "Found" if find_logo(team) else "Missing"
                )
                st.dataframe(
                    comparison,
                    use_container_width=True,
                    hide_index=True
                )


# --------------------------------------------------

def show_history_power_cards(data, rank_column, score_column, title):
    if data.empty or "Team" not in data.columns:
        st.info("No rankings are available for this selection.")
        return
    board = data.copy()
    if rank_column in board.columns:
        board[rank_column] = pd.to_numeric(board[rank_column], errors="coerce")
        board = board.sort_values(rank_column, na_position="last")
    elif score_column in board.columns:
        board[score_column] = pd.to_numeric(board[score_column], errors="coerce")
        board = board.sort_values(score_column, ascending=False, na_position="last")
    else:
        st.warning(f"{title} requires a rank or score column.")
        return
    cards = []
    for i, row in board.dropna(subset=["Team"]).reset_index(drop=True).iterrows():
        rank = row[rank_column] if rank_column in board.columns else i + 1
        rank = str(int(rank)) if pd.notna(rank) else str(i + 1)
        cards.append(
            f'<div class="history-ranking-card"><div class="history-ranking-number">{rank}</div>'
            f'<div class="history-ranking-team">{get_logo_html(str(row["Team"]))}</div></div>'
        )
    st.markdown(f"**{title}**")
    st.html('<div class="history-ranking-grid">' + "".join(cards) + '</div>')


def show_history_comparison(history, season):
    st.subheader("Week-to-Week Team Comparisons")
    data = history[history["Season"] == season].copy()
    teams = sorted(data["Team"].dropna().astype(str).unique())
    chosen = st.multiselect("Teams to compare", teams, default=teams[:4], key="history_compare")
    if not chosen:
        return
    metrics = {
        "Overall score": ("Overall_Score", False),
        "Offensive score": ("Offense_Score", False),
        "Defensive score": ("Defense_Score", False),
        "Special-teams score": ("Special_Teams_Score", False),
        "Overall rank": ("Rank", True),
        "Offensive rank": ("Offense_Rank", True),
        "Defensive rank": ("Defense_Rank", True),
        "Special-teams rank": ("Special_Teams_Rank", True)
    }
    available = {k: v for k, v in metrics.items() if v[0] in data.columns}
    if not available:
        st.info("No score or category-rank columns are available for comparison.")
        return
    metric = st.selectbox("Comparison metric", list(available), key="history_compare_metric")
    column, is_rank = available[metric]
    data = data[data["Team"].astype(str).isin(chosen)].copy()
    data["Week"] = pd.to_numeric(data["Week"], errors="coerce")
    data[column] = pd.to_numeric(data[column], errors="coerce")
    chart = data.pivot_table(index="Week", columns="Team", values=column, aggfunc="last").sort_index()
    if is_rank:
        chart = 33 - chart
        st.caption("Higher on this chart means a better ranking; rank #1 is highest.")
        st.line_chart(chart, y_label="Ranking strength (33 − rank)")
    else:
        st.caption("Compare each team's saved weekly score.")
        st.line_chart(chart, y_label="Weekly score")


# RANKING HISTORY

with history_tab:
    if not RANKING_HISTORY_FILE.exists():
        st.warning("NFL_Ranking_History.csv was not found beside the dashboard file.")
    else:
        history = pd.read_csv(RANKING_HISTORY_FILE)
        required = {"Team", "Rank", "Season", "Week"}
        missing = required - set(history.columns)
        if missing:
            st.warning("History file is missing: " + ", ".join(sorted(missing)))
        else:
            for col in ["Season", "Week", "Rank"]:
                history[col] = pd.to_numeric(history[col], errors="coerce")
            history = history.dropna(subset=["Season", "Week", "Team"]).copy()
            if history.empty:
                st.info("No valid ranking history records were found.")
            else:
                seasons = sorted(history["Season"].astype(int).unique())
                latest_season = max(seasons)
                c1, c2 = st.columns(2)
                with c1:
                    selected_season = st.number_input(
                        "Season", min_value=1900, max_value=2100,
                        value=int(latest_season), step=1, key="history_season_entry"
                    )
                season_history = history[history["Season"] == selected_season]
                week_default = int(season_history["Week"].max()) if not season_history.empty else 1
                with c2:
                    selected_week = st.number_input(
                        "Week", min_value=1, max_value=22,
                        value=min(week_default, 22), step=1, key="history_week_entry"
                    )

                week_history = season_history[season_history["Week"] == selected_week].copy()
                if week_history.empty:
                    st.warning(
                        f"No records found for {int(selected_season)}, Week {int(selected_week)}. "
                        "Add that week's records to NFL_Ranking_History.csv and refresh."
                    )
                else:
                    st.subheader(f"{int(selected_season)} Season — Week {int(selected_week)}")
                    show_history_power_cards(
                        week_history, "Rank", "Overall_Score",
                        f"Week {int(selected_week)} Overall Power Rankings"
                    )
                    for label, rank_col, score_col in [
                        ("Offense", "Offense_Rank", "Offense_Score"),
                        ("Defense", "Defense_Rank", "Defense_Score"),
                        ("Special Teams", "Special_Teams_Rank", "Special_Teams_Score")
                    ]:
                        if rank_col in week_history.columns or score_col in week_history.columns:
                            with st.expander(f"Week {int(selected_week)} {label} Power Rankings"):
                                show_history_power_cards(week_history, rank_col, score_col, f"{label} Rankings")

                if not season_history.empty:
                    show_history_comparison(history, selected_season)

                st.caption(
                    "Enter the season and week above to view saved rankings. "
                    "To add a new week, add its team ranks and scores to NFL_Ranking_History.csv, "
                    "then refresh the dashboard."
                )


# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "Green = favorite | Red = underdog. "
    "Completed games show actual scores and prediction results. Model Performance summarizes winner accuracy and score errors. "
    "Current rankings use NFL_Team_Rankings.csv; Ranking History stores weekly snapshots."
)
#streamlit run NFL_Dashboard.py