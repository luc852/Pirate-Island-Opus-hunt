"""Score persistence: load/save scores.json in the project folder.

The roster is open-ended: any name a player types is registered on the spot,
and names are matched case-insensitively so "luc" and "Luc" are one pirate.
"""
import json
import os

SCORES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scores.json")

MAX_NAME_LEN = 14

DEFAULT_DATA = {
    "players": {},
    "overall_best": {"name": "", "score": 0},
}


def clean_name(raw):
    """Trim, collapse inner whitespace and cap the length of a typed name."""
    return " ".join(str(raw).split())[:MAX_NAME_LEN]


def load_scores():
    if not os.path.exists(SCORES_PATH):
        return json.loads(json.dumps(DEFAULT_DATA))
    try:
        with open(SCORES_PATH, "r") as f:
            loaded = json.load(f)
    except (json.JSONDecodeError, OSError):
        return json.loads(json.dumps(DEFAULT_DATA))

    data = json.loads(json.dumps(DEFAULT_DATA))
    for name, entry in (loaded.get("players") or {}).items():
        name = clean_name(name)
        if not name:
            continue
        try:
            best = int(entry.get("best_score", 0))
            games = int(entry.get("games_played", 0))
        except (AttributeError, TypeError, ValueError):
            continue
        # A file edited by hand may hold two spellings of one pirate; fold them.
        existing = find_player(data, name)
        if existing:
            data["players"][existing]["best_score"] = max(
                data["players"][existing]["best_score"], best)
            data["players"][existing]["games_played"] += games
        else:
            data["players"][name] = {"best_score": best, "games_played": games}

    refresh_overall_best(data)
    return data


def save_scores(data):
    with open(SCORES_PATH, "w") as f:
        json.dump(data, f, indent=2)


def find_player(data, name):
    """Return the registered spelling matching `name`, or None."""
    key = clean_name(name).lower()
    if not key:
        return None
    for registered in data["players"]:
        if registered.lower() == key:
            return registered
    return None


def refresh_overall_best(data):
    best_name, best_score = "", 0
    for name, entry in data["players"].items():
        if entry["best_score"] > best_score:
            best_name, best_score = name, entry["best_score"]
    data["overall_best"] = {"name": best_name, "score": best_score}
    return data


def register_player(data, name):
    """Add the pirate if new, and return the canonical spelling of the name."""
    existing = find_player(data, name)
    if existing:
        return existing
    name = clean_name(name)
    data["players"][name] = {"best_score": 0, "games_played": 0}
    return name


def best_score(data, name):
    existing = find_player(data, name)
    return data["players"][existing]["best_score"] if existing else 0


def ranking(data):
    """(name, best_score) pairs, best first, ties broken alphabetically."""
    return sorted(((n, e["best_score"]) for n, e in data["players"].items()),
                  key=lambda pair: (-pair[1], pair[0].lower()))


def record_score(data, player_name, score):
    """Register the pirate if needed, then keep their best run and the overall best."""
    name = register_player(data, player_name)
    entry = data["players"][name]
    entry["games_played"] += 1
    if score > entry["best_score"]:
        entry["best_score"] = score
    refresh_overall_best(data)
    save_scores(data)
    return data
