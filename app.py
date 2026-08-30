import concurrent.futures
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from flask import Flask, render_template
import requests

app = Flask(__name__)

BASE_DOMAIN = "https://hkta.tournamentsoftware.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def get_global_profile_url(tournament_player_url):
    """Fetches a tournament player page and extracts the real global profile link."""
    if not tournament_player_url:
        return None

    try:
        resp = requests.get(tournament_player_url, headers=HEADERS, timeout=5)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find the anchor tag pointing to /player-profile/
        profile_anchor = soup.find(
            "a", href=lambda h: h and "/player-profile/" in h
        )

        if profile_anchor and profile_anchor.get("href"):
            return urljoin(BASE_DOMAIN, profile_anchor["href"])

        # Fallback to tournament page if global profile link is missing
        return tournament_player_url
    except Exception:
        return tournament_player_url


@app.route("/")
def home():
    url = f"{BASE_DOMAIN}/tournament/C3333DC3-695D-411B-A777-85362D6AE1F8/draw/2"
    players_raw = []
    seen = set()

    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract player elements from the draw page
        player_items = soup.find_all("li", class_="js-asg-result-item")

        for item in player_items:
            name = item.get("data-asg-title") or item.get_text(strip=True)
            name = name.strip()

            if not name or name == "Bye":
                continue

            player_id = item.get("data-asg-value")
            tourn_url = (
                f"{BASE_DOMAIN}/tournament/C3333DC3-695D-411B-A777-85362D6AE1F8/player/{player_id}"
                if player_id
                else None
            )

            if name not in seen:
                seen.add(name)
                players_raw.append({"Player": name, "tourn_url": tourn_url})

    except requests.exceptions.RequestException as e:
        print(f"Error fetching draw: {e}")

    # Resolve global profile links concurrently to keep speed high
    players_data = []

    def fetch_player_profile(player):
        global_url = get_global_profile_url(player["tourn_url"])
        return {"Player": player["Player"], "Details": global_url}

    # Parallel requests (max 10 workers) prevent slow loading
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        players_data = list(executor.map(fetch_player_profile, players_raw))

    return render_template("player_list.html", players_data=players_data)


if __name__ == "__main__":
    app.run(debug=True)