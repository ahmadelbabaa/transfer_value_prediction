# J1 League – Transfer Value Prediction

Predicting football player market values from on-pitch performance using StatsBomb event data and Transfermarkt valuations for the J1 League season.

---

## Project Structure

```
transfer_value_prediction/
├── data_prep/
│   ├── scraper.py                        # Scrapes market values from Transfermarkt
│   ├── j1_league_player_values.csv       # Raw scraped market values (698 players)
│   ├── sb_events.json                    # StatsBomb event data – 1.24M events, 376 matches (Git LFS)
│   ├── build_dataset.ipynb               # Builds the merged modelling dataset
│   └── j1_player_value_statsbomb_merged.csv  # Final modelling dataset (one row per player)
└── README.md
```

---

## Data Sources

### StatsBomb Event Data (`sb_events.json`)
Raw event-level data for every match in the J1 League season, provided by StatsBomb. Each event is a single on-pitch action (pass, shot, tackle, pressure, etc.) with the following key fields:

- `player.id`, `player.name`, `team.name`, `match_id`
- `type.name` — event type (Pass, Shot, Pressure, Duel, Interception, …)
- `minute`, `period` — when the event occurred
- `shot.statsbomb_xg` — expected goals for shot events
- `pass.goal_assist`, `pass.shot_assist`, `pass.assisted_shot_id` — assist/key-pass flags
- `tactics.lineup` — starting XI for each team per match
- `substitution.*` — who came on/off and at what minute

The file is ~1.5 GB and is stored in this repository via **Git LFS**. Run `git lfs pull` after cloning to download it.

### Transfermarkt Market Values (`j1_league_player_values.csv`)
Scraped from [transfermarkt.com](https://www.transfermarkt.com/j1-league/marktwerteverein/wettbewerb/JAP1) using `data_prep/scraper.py`.

| Column | Description |
|---|---|
| `player` | Player name as shown on Transfermarkt |
| `team` | Club name |
| `market_value_eur` | Numeric market value in euros |
| `market_value_raw` | Original string (e.g. `€1.50m`) |

698 players scraped across all 20 J1 League clubs. 106 players had no listed value and were excluded from modelling.

---

## Pipeline

### Step 1 — Scrape Market Values (`scraper.py`)
Fetches the J1 League team list from Transfermarkt, visits each of the 20 team squad pages, and extracts player names and market values. Output: `j1_league_player_values.csv`.

```bash
python data_prep/scraper.py
```

### Step 2 — Build Modelling Dataset (`build_dataset.ipynb`)
Reads both data sources and produces a player-level dataset with performance statistics and market values merged together.

**What the notebook does:**

1. **Loads** `sb_events.json` and `j1_league_player_values.csv`.
2. **Cleans** Transfermarkt names (lowercase, accent removal, whitespace normalisation) for joining.
3. **Computes minutes played** per player from `Starting XI` and `Substitution` events — starters play until they are subbed off or the match ends; substitutes play from the minute they enter.
4. **Aggregates performance metrics** across all 376 matches into season totals per player:
   - Goals, shots, xG
   - xA (expected assists — derived by linking assist passes to their shot's xG)
   - Key passes, assists, passes, completed passes, progressive passes
   - Pressures, interceptions, tackles, dribbles, successful dribbles
5. **Creates per-90 versions** of every metric (e.g. `xG_per90`, `pressures_per90`).
6. **Merges** StatsBomb and Transfermarkt on cleaned player name + team name (inner join).
7. **Filters** to players with ≥ 600 minutes played and a valid market value.
8. **Adds** `log_market_value = log(market_value_eur)` as the primary modelling target.
9. **Saves** the result to `j1_player_value_statsbomb_merged.csv`.

---

## Final Dataset (`j1_player_value_statsbomb_merged.csv`)

105 players × 36 columns. One row per player for the full season.

| Column group | Columns |
|---|---|
| Identity | `player_id`, `player_name`, `team_name` |
| Volume | `minutes_played`, `goals`, `assists`, `shots`, `xG`, `xA`, `key_passes`, `passes`, `completed_passes`, `progressive_passes`, `pressures`, `interceptions`, `tackles`, `dribbles`, `successful_dribbles`, `pass_completion_pct` |
| Per 90 | Same columns with `_per90` suffix |
| Target | `market_value_eur`, `market_value_raw`, `log_market_value` |

**Summary statistics:**

| Metric | Value |
|---|---|
| Players | 105 |
| Teams represented | 11 |
| Median market value | €500,000 |
| Median minutes played | ~2,077 |

---

## Setup

```bash
# Clone and pull LFS data
git clone https://github.com/ahmadelbabaa/transfer_value_prediction.git
cd transfer_value_prediction
git lfs pull

# Install dependencies
pip install requests beautifulsoup4 lxml pandas numpy jupyter

# Run scraper (optional — CSV already committed)
python data_prep/scraper.py

# Build dataset
jupyter notebook data_prep/build_dataset.ipynb
```
