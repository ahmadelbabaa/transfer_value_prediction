import time
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.transfermarkt.com/",
}
BASE_URL = "https://www.transfermarkt.com"
LEAGUE_URL = f"{BASE_URL}/j1-league/marktwerteverein/wettbewerb/JAP1"


def get_soup(url: str, retries: int = 3) -> BeautifulSoup:
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except requests.RequestException as e:
            if attempt < retries - 1:
                time.sleep(3)
            else:
                raise e


def parse_market_value(text: str) -> float | None:
    """Convert '€12.50m' or '€500k' to a float in euros."""
    text = text.strip().replace("\xa0", "").replace(",", ".")
    match = re.search(r"([\d.]+)\s*([mk]?)", text, re.IGNORECASE)
    if not match:
        return None
    value = float(match.group(1))
    suffix = match.group(2).lower()
    if suffix == "m":
        value *= 1_000_000
    elif suffix == "k":
        value *= 1_000
    return value


def get_team_links(soup: BeautifulSoup) -> list[dict]:
    teams = []
    seen = set()
    for row in soup.select("table.items tbody tr"):
        link_tag = row.select_one("td.hauptlink a[href]")
        if not link_tag:
            continue
        href = link_tag["href"]
        # Team links contain /verein/; player links contain /spieler/ — skip players
        if "/verein/" not in href or "/spieler/" in href:
            continue
        # Convert market-value URL to squad (kader) URL
        # e.g. /gamba-osaka/marktwerteverein/verein/123 -> /gamba-osaka/kader/verein/123
        squad_href = href.replace("marktwerteverein", "kader")
        if squad_href in seen:
            continue
        seen.add(squad_href)
        teams.append({"name": link_tag.get_text(strip=True), "url": BASE_URL + squad_href})
    return teams


def scrape_squad(team_name: str, squad_url: str) -> list[dict]:
    soup = get_soup(squad_url)
    players = []
    for row in soup.select("table.items tbody tr.odd, table.items tbody tr.even"):
        name_tag = row.select_one("td.hauptlink a[href]")
        value_tag = row.select_one("td.rechts.hauptlink")
        if not name_tag:
            continue
        player_name = name_tag.get_text(strip=True)
        raw_value = value_tag.get_text(strip=True) if value_tag else ""
        market_value = parse_market_value(raw_value) if raw_value else None
        players.append({
            "player": player_name,
            "team": team_name,
            "market_value_eur": market_value,
            "market_value_raw": raw_value,
        })
    return players


def main():
    print("Fetching J1 League team list...")
    league_soup = get_soup(LEAGUE_URL)
    teams = get_team_links(league_soup)
    print(f"Found {len(teams)} teams.")

    all_players = []
    for i, team in enumerate(teams, 1):
        print(f"[{i}/{len(teams)}] Scraping {team['name']}...")
        try:
            players = scrape_squad(team["name"], team["url"])
            all_players.extend(players)
            print(f"  -> {len(players)} players")
        except Exception as e:
            print(f"  -> ERROR: {e}")
        time.sleep(2)  # polite delay between requests

    df = pd.DataFrame(all_players)
    output_path = "j1_league_player_values.csv"
    df.to_csv(output_path, index=False)
    print(f"\nDone. {len(df)} players saved to {output_path}")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
