# Pirate Island Coin Hunt

A small pygame arcade game: sail between islands, collect every coin, dodge the
monsters and the puddles, and get your name onto the leaderboard.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![pygame](https://img.shields.io/badge/pygame-2.5%2B-green)

## Playing in a browser

The game is compiled to WebAssembly and deployed as a static site, so it runs
in the browser with nothing to install.

## Playing on the desktop

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
| `build_web.py` | Compiles the game to WebAssembly into `web/` |
| `web/` | The built browser version; this is what Vercel serves |

The `*.dc.html` files and `canvas.json` are design mockups of the screens, not
part of the running game.

## Rebuilding the browser version

```bash
pip install pygbag
python build_web.py
```

Then commit `web/` — that folder is what gets served. The same source runs both
ways; three details make the browser build work:

- `main.py` imports `pygame` explicitly, because pygbag reads that file's
  imports to decide what to load into the runtime.
- The frame is scaled with `transform.scale` rather than `smoothscale` on the
  web. `smoothscale` costs most of the frame budget in WebAssembly, which
  starves the browser's event delivery and makes the game stop responding.
- `VIDEORESIZE` only rebuilds the display on a genuinely new size, otherwise
  the canvas oscillates and the game never gets to read input.

**Scores in the browser are per-browser.** There is no shared server: they live
in that browser profile's local storage, so everyone using the same browser on
the same machine shares one roster, and nobody else sees it. The desktop version
still uses `scores.json`.

## Credits

Coin artwork from [Kenney](https://kenney.nl) under CC0.
