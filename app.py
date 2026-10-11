from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import os

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
CORS(app)  # Enable CORS for all routes

# Serve the main HTML file
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

# Serve static files (CSS, JS)
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(BASE_DIR, path)

def get_player_stats(profile_url):
    """Fetch player statistics from their profile page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(profile_url, headers=headers, timeout=10)

        if not response.ok:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        stats = {}

        # Find Career Win-Loss record
        career_elem = soup.find('dt', string='Career')
        if career_elem:
            career_value = career_elem.find_next('dd')
            if career_value:
                text = career_value.get_text(strip=True)
                # Format: "111 / 89 (200)"
                match = re.search(r'(\d+)\s*/\s*(\d+)\s*\((\d+)\)', text)
                if match:
                    wins = int(match.group(1))
                    losses = int(match.group(2))
                    total = int(match.group(3))
                    stats['wins'] = wins
                    stats['losses'] = losses
                    stats['winRate'] = f"{(wins/total*100):.1f}%" if total > 0 else "0%"

        # Find World Tennis Number (ranking)
        wtn_elem = soup.find('span', string='Singles')
        if wtn_elem:
            parent = wtn_elem.find_parent('span', class_='tag-duo')
            if parent:
                value_span = parent.find('span', class_='tag-duo__value')
                if value_span:
                    # Extract just the number
                    wtn_text = value_span.get_text(strip=True)
                    wtn_match = re.search(r'(\d+\.?\d*)', wtn_text)
                    if wtn_match:
                        stats['ranking'] = f"WTN {wtn_match.group(1)}"

        # Get recent match results
        recent_matches = soup.find_all('span', class_='match__status', limit=5)
        if recent_matches:
            results = []
            for match in recent_matches:
                if 'tag--success' in match.get('class', []):
                    results.append('W')
                elif 'tag--danger' in match.get('class', []):
                    results.append('L')
            if results:
                stats['lastMatch'] = ' '.join(results[:5])

        return stats if stats else None

    except Exception as e:
        print(f"Error fetching stats: {e}")
        return None


def get_player_profile_url(player_name, base_url):
    """Try to find the actual player profile UUID by searching"""
    try:
        # Try searching for the player
        search_url = f'{base_url}/find/player?q={player_name.replace(" ", "+")}'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(search_url, headers=headers, timeout=5)

        if response.ok:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Look for player-profile links
            profile_link = soup.find('a', href=re.compile(r'/player-profile/[A-F0-9-]+'))
            if profile_link:
                href = profile_link.get('href')
                return base_url + href if not href.startswith('http') else href
    except:
        pass

    # Fallback to search URL
    return f'{base_url}/find/player?q={player_name.replace(" ", "+")}'


@app.route('/api/draw', methods=['GET'])
def get_draw():
    """Fetch and parse tournament draw"""
    draw_url = request.args.get('url')
    fetch_profiles = request.args.get('fetch_profiles', 'false').lower() == 'true'

    if not draw_url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        # Fetch the draw page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(draw_url, headers=headers, timeout=10)
        response.raise_for_status()

        base_url = 'https://hkta.tournamentsoftware.com'

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Method 1: Look for data-asg-title attributes (player names in draw)
        player_items = soup.find_all('li', attrs={'data-asg-title': True, 'data-asg-value': True})

        players_dict = {}
        for item in player_items:
            name = item.get('data-asg-title', '').strip()
            player_id = item.get('data-asg-value', '').strip()

            # Skip bye, winners, empty names
            if (name and
                'bye' not in name.lower() and
                'winner' not in name.lower() and
                not name.lower().startswith('q-') and
                len(name) > 1):

                if name not in players_dict:
                    # Try to get real profile URL if requested
                    if fetch_profiles:
                        profile_url = get_player_profile_url(name, base_url)
                        # Fetch player stats from their profile
                        stats = get_player_stats(profile_url)
                        if stats:
                            players_dict[name] = {
                                'name': name,
                                'profileUrl': profile_url,
                                'playerId': player_id,
                                'ranking': stats.get('ranking', 'TBD'),
                                'wins': stats.get('wins', 0),
                                'losses': stats.get('losses', 0),
                                'winRate': stats.get('winRate', 'N/A'),
                                'lastMatch': stats.get('lastMatch', 'N/A')
                            }
                        else:
                            players_dict[name] = {
                                'name': name,
                                'profileUrl': profile_url,
                                'playerId': player_id,
                                'ranking': 'TBD',
                                'wins': '-',
                                'losses': '-',
                                'winRate': 'N/A',
                                'lastMatch': 'N/A'
                            }
                    else:
                        profile_url = f'{base_url}/find/player?q={name.replace(" ", "+")}'
                        players_dict[name] = {
                            'name': name,
                            'profileUrl': profile_url,
                            'playerId': player_id,
                            'ranking': 'TBD',
                            'wins': '-',
                            'losses': '-',
                            'winRate': 'N/A',
                            'lastMatch': 'Check profile for stats'
                        }

        # Method 2: Also check for actual /player-profile/ links (if they exist)
        profile_links = soup.find_all('a', href=re.compile(r'/player-profile/'))
        for link in profile_links:
            name = link.get_text(strip=True)
            href = link.get('href')

            if (name and
                'bye' not in name.lower() and
                'winner' not in name.lower() and
                len(name) > 1):

                if name not in players_dict:
                    full_url = base_url + href if not href.startswith('http') else href
                    players_dict[name] = {
                        'name': name,
                        'profileUrl': full_url,
                        'ranking': 'TBD',
                        'wins': '-',
                        'losses': '-',
                        'winRate': 'N/A',
                        'lastMatch': 'Click profile for details'
                    }

        players = list(players_dict.values())

        return jsonify({
            'success': True,
            'playerCount': len(players),
            'players': players
        })

    except requests.RequestException as e:
        return jsonify({'error': f'Failed to fetch draw: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Error parsing draw: {str(e)}'}), 500


@app.route('/api/player', methods=['GET'])
def get_player():
    """Fetch player profile statistics"""
    player_url = request.args.get('url')

    if not player_url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(player_url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract player name
        name_elem = soup.find('h1')
        name = name_elem.get_text(strip=True) if name_elem else 'Unknown'

        # Look for stats in various possible locations
        # Try to find ranking, record, etc.
        stats_dict = {
            'name': name,
            'ranking': 'N/A',
            'wins': 0,
            'losses': 0,
            'winRate': 'N/A',
            'lastMatch': 'N/A'
        }

        # Try to find player stats from tables or divs
        # The actual structure may vary, so we'll look for common patterns
        stat_rows = soup.find_all(['tr', 'div'], class_=re.compile(r'stat|record|ranking', re.I))

        for row in stat_rows:
            text = row.get_text(strip=True).lower()
            if 'ranking' in text:
                # Try to extract ranking number
                numbers = re.findall(r'\d+', text)
                if numbers:
                    stats_dict['ranking'] = numbers[0]

        # Look for match history to get win/loss record
        matches = soup.find_all('tr', class_=re.compile(r'match', re.I))
        wins = 0
        losses = 0

        for match in matches[:20]:  # Check last 20 matches
            text = match.get_text().lower()
            if 'won' in text or 'win' in text:
                wins += 1
            elif 'lost' in text or 'loss' in text:
                losses += 1

        if wins > 0 or losses > 0:
            stats_dict['wins'] = wins
            stats_dict['losses'] = losses
            total = wins + losses
            stats_dict['winRate'] = f"{(wins/total*100):.1f}%" if total > 0 else 'N/A'

        return jsonify({
            'success': True,
            'stats': stats_dict
        })

    except Exception as e:
        return jsonify({'error': f'Error fetching player: {str(e)}'}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("HKCTA Draw Analyzer Server")
    print("=" * 60)
    print("\n✓ Server starting on http://localhost:5000")
    print("\n🌐 Open your browser and go to:")
    print("   http://localhost:5000")
    print("\nNo need for a separate web server!")
    print("\nPress Ctrl+C to stop the server\n")
    print("=" * 60 + "\n")

    app.run(debug=True, port=5000)