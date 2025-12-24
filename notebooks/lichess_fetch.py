"""
Docstring for notebooks.lichess_fetch
Usage: python fetch_lichess_user_data.py <lichess_username>
URLs used:
    1. Let's get the User's profile
        https://lichess.org/api/user/mock_user_name
    
    2. Fetch last 20 games from the user.     
        https://lichess.org/api/games/user/mock_user_name

    3. Is the User online?
        https://lichess.org/api/users/status?ids=mock_user_name&withGameIds=true

    4. Let's get the user's current game.
        http://lichess.org/api/user/mock_user_name/current-game

Comment JSON Dumps.
"""



import requests
import sys
import json


BASE_URL = "https://lichess.org"
USERNAME = sys.argv[1] if len(sys.argv) > 1 else None

if not USERNAME:
    print("Usage: python fetch_lichess_user_data.py <lichess_username>")
    sys.exit(1)



# Let's get the User's profile
def fetch_user_profile(username: str):
    url = f"{BASE_URL}/api/user/{username}"
    print(f"\n=== FETCHING USER PROFILE: {url} ===\n")

    r = requests.get(url, headers={"Accept": "application/json"})
    r.raise_for_status()

    data = r.json()
    print(json.dumps(data, indent=2))
    with open('user_profile.json', 'w') as f:
        f.write(json.dumps(data, indent = 2))


# Get past 20 games from the User
def fetch_user_games(username: str, max_games: int = 20):
    """
    Fetch recent games as NDJSON and print each game JSON.
    """
    url = f"{BASE_URL}/api/games/user/{username}"
    params = {
        "max": max_games,
        "moves": True,
        "pgnInJson": True,
        "opening": True,
        "clocks": True,
        "evals": False,
    }

    headers = {
        "Accept": "application/x-ndjson"
    }

    print(f"\n=== FETCHING LAST {max_games} GAMES (NDJSON) ===\n")
    game_dict = {}
    with requests.get(url, params=params, headers=headers, stream=True) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            game = json.loads(line.decode("utf-8"))
            print(json.dumps(game, indent=2))
            print("\n" + "=" * 80 + "\n")
            game_dict[len(game_dict)] = game
        with open('user_games.json', 'w') as f:
            f.write(json.dumps(game_dict, indent=2))


# Is the user even online?
def is_user_playing(username: str, timeout_s: int = 10):
    """
        Check if the user is playing a game or not. 
        # https://lichess.org/api/users/status?ids=mock_user_name&withGameIds=true
        Ret: [
                {
                    "name":"mock_user_name",
                    "id":"mock_user_name",
                    "online":true,
                    "playing":true,
                    "playingId":"rsHrwn8g"
                }
            ]
    """
    
    url = f"{BASE_URL}/api/users/status"
    params = {"ids": username, "withGameIds": "true"}
    headers = {"Accept": "application/json"}

    r = requests.get(url, params=params, headers=headers, timeout=timeout_s)
    r.raise_for_status()

    print("\n=== Is the User Active? ===\n")
    data = r.json()
    print(data)

    if isinstance(data, list):
        data = data[0]
    if data.get('playingId'):
        return True
    return False


# Get the user's current game
def fetch_current_game(username: str, timeout_s : int = 10):
    """
    Docstring for fetch_current_game
    
    :param username: Description
    :type username: str
    # http://lichess.org/api/user/mock_user_name/current-game


    """
    url = f"https://lichess.org/api/user/{username}/current-game"
    headers = {"Accept": "application/json"}

    # Optional params you may want:
    params = {
        "moves": "true",
        "clocks": "true",
        "opening": "true",
        # "pgnInJson": "true",  # uncomment if you also want PGN embedded in the JSON
    }

    r = requests.get(url, params=params, headers=headers, timeout=timeout_s)
    r.raise_for_status()

    print("\n=== CURRENT GAME ===\n")
    print(r.json())
    return




def main():
    fetch_user_profile(USERNAME)
    fetch_user_games(USERNAME, max_games=20)
    currently_gaming = is_user_playing(USERNAME)

    if currently_gaming:
        fetch_current_game(USERNAME)


if __name__ == "__main__":
    main()
    
