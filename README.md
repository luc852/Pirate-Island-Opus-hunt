# Pirate Island Coin Hunt

A small pygame arcade game: sail between islands, collect every coin, dodge the
monsters and the puddles, and get your name onto the leaderboard.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![pygame](https://img.shields.io/badge/pygame-2.5%2B-green)

## Playing

```bash
pip install -r requirements.txt
python main.py
```

On Windows you can also just double-click `Play PirateGame.bat`.

**Controls** — arrow keys or `WASD` to move. That's the whole game.

You start with 3 lives across all levels. Each coin is 10 points, clearing an
island adds 50. Touching a monster or a puddle costs a life and grants a short
window of invincibility.

## Players and scores

The title screen has two ways aboard:

- **Returning pirate** — pick your name from the list, which is ranked by best
  score so you can see who is ahead.
- **New pirate** — type a name. If it matches someone already registered the two
  are consolidated, so `luc`, `Luc` and `LUC` are all the same pirate. The
  *Save my name and score* checkbox is on by default; unticking it gives you a
  guest run that is played but never recorded.

Scores live in `scores.json` next to the code. Each player keeps a best score and
a count of games played, and the overall best is recomputed from the roster.

## Layout

| File | What it holds |
| --- | --- |
| `main.py` | Entry point |
| `game.py` | Game loop, screens, HUD, scoring |
| `sprites.py` | Player, monsters, coins, and the hand-drawn artwork |
| `levels.py` | Level grids and per-level monster tuning |
| `data.py` | The player roster and score persistence |
| `ui.py` | Title-screen widgets: combo box, text field, checkbox |
| `assets/` | Coin sprites (Kenney, CC0 — see `assets/images/KENNEY_LICENSE.txt`) |

The `*.dc.html` files and `canvas.json` are design mockups of the screens, not
part of the running game.

## Credits

Coin artwork from [Kenney](https://kenney.nl) under CC0.
