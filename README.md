# Pirate Island Coin Hunt

A small pygame arcade game: sail between five islands from dawn to a lantern-lit
night, collect every doubloon, crack the ciphered clue to dig up each island's
buried chest, survive storms, the Kraken and a ghost ship's cannons - and if you
find all five chests, follow the map to a secret sixth island.

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

**Controls**

| Key | Action |
| --- | --- |
| Arrows / `WASD` | Move |
| `Space` / `E` | Dig where you stand |
| `P` / `Esc` | Pause - the ship's log shows the clue and, once known, a cipher decoder |
| `Q` (while paused) | Abandon the voyage (not recorded) |
| `M` (in game), `F2` (title) | Sound on/off |
| `Enter` / `Space` | Continue on every card and end screen |

The title screen works without a mouse too: just start typing a name, or use
Up/Down to pick a returning pirate, then `Enter`.

You start with 3 lives across all islands. Touching a crab, a tide pool or a
peril's strike costs a life and grants a short window of invincibility.

### Mysteries

- **Buried chests and the cipher.** Every island hides a chest, located from a
  skull-shaped rock: *"FROM THE SKULL ROCK, THREE SOUTH THEN TWO WEST"* (one
  pace = one tile). The clue is painted on the scroll along the bottom of the
  island, Caesar-shifted. Each doubloon deciphers more letters, and once enough
  are known the key appears (also as a full decoder in the pause log). Dig on the
  spot with `Space` - but before the last doubloon, because leaving the island
  buries the chest for good. Every letter still ciphered when you dig is worth a
  bonus, so cracking the shift by hand pays.
- **Random perils** (from the second island; a storm can hit the first):
  *Storms* bring rain, lightning and a wind that pushes you sideways, but gold
  is worth double while they last. *The Kraken* slams tentacles where you are
  standing, after a rippling warning. *A ghost ship* fires volleys of
  cannonballs at red target marks. Survive any of them untouched for a bonus.
- **The secret island.** Each chest is a map piece. With all five, the last
  island's exit leads to *Isla Calavera* under a blood moon, where ghost crabs
  hunt in the dark and the legendary chest unlocks the secret ending.

### Scoring

| Source | Points |
| --- | --- |
| Doubloon | 10 (20 during a storm) |
| Combo | grabbing the next doubloon within 2.2 s keeps the chain: x2 from 3 in a row, x3 from 6, x4 from 10 |
| Island cleared | 50 |
| Swift sailing | 4 per second under par (25 s + 3.5 s per doubloon) |
| Untouched island | 100 |
| Buried chest | 250, plus 15 per letter still ciphered |
| Peril survived untouched | 75 storm, 120 ghost ship, 150 Kraken |
| Wasted dig | -5 |
| Lives left at the end of a won voyage | 100 each |
| Legend of Isla Calavera | 1000 |

The HUD shows lives, doubloons, map pieces, the active peril's countdown, the
combo multiplier with its timer ring, and a rolling score. Every island ends
with its own tally, and every voyage with an animated breakdown of where the
points came from, next to the Hall of Fame.

## Players and scores

The title screen has two ways aboard:

- **Returning pirate** — pick your name from the list, which is ranked by best
  score so you can see who is ahead.
- **New pirate** — type a name. If it matches someone already registered the two
  are consolidated, so `luc`, `Luc` and `LUC` are all the same pirate. The
  *Save my name and score* checkbox is on by default; unticking it gives you a
  guest run that is played but never recorded.

Scores live in `scores.json` next to the code. Each player keeps a best score, a
count of games played, their longest coin chain, most chests in one voyage and
whether they found the legend; the overall best is recomputed from the roster.
The ten best voyages are kept as the Hall of Fame. Older files without these
fields load fine, and their best scores seed the Hall of Fame.

## Layout

| File | What it holds |
| --- | --- |
| `main.py` | Entry point |
| `game.py` | Game loop, screens, HUD, and wiring everything together |
| `scoring.py` | Combo multiplier and the points ledger behind the breakdown |
| `mysteries.py` | Buried chests and their cipher, storms, the Kraken, the ghost ship |
| `effects.py` | Animated sea, particles, popups, shake, rain, clouds, night lantern |
| `audio.py` | Sound effects and ambience, synthesized at start-up (no audio files) |
| `sprites.py` | Player, monsters, coins, and the hand-drawn artwork |
| `levels.py` | Level grids, names, time of day, perils, and the secret island |
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

Then commit `web/` — that folder is what gets served. New modules must be added
to `GAME_FILES` in `build_web.py`, or the browser build will not include them.

To try the build locally, serve `web/` and open it at `http://127.0.0.1:<port>`
rather than `localhost`: on `localhost` pygbag assumes its own dev server and
tries to fetch the runtime from port 8000. The same source runs both
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
