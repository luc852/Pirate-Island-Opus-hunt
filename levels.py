"""Level layouts.

Grid legend:
  '#' wall / obstacle
  '.' open sand
  '~' puddle (hazard)
  'C' coin
  'M' monster spawn
  'P' player start

All levels are generated from a recursive-backtracker maze (guaranteed fully
connected) with a "braid" factor controlling how open vs. maze-like the level
feels. Later levels are less braided -> tighter, more maze-like.
"""

TILE_SIZE = 40

LEVEL_1 = [
    '#####################',
    '#P..........C.......#',
    '#.#.#.#.#.#.#.#~#.#.#',
    '#...C...#M..........#',
    '#.#.#C#.#.#.#.###.#.#',
    '#.........#....C..~C#',
    '###.#.#.#.#.#.#.###.#',
    '#..........C........#',
    '#.#C###.#.#.#~#.#.#M#',
    '#.........#.......#.#',
    '#.#.#.#.#.#.#.#.#.#.#',
    '#.........C.........#',
    '#####################',
]

LEVEL_2 = [
    '#####################',
    '#P#..C.......C..#...#',
    '#.#.#####.#C#~#.#.###',
    '#.#.........#...#...#',
    '#.#.###.###.#.#.#.#.#',
    '#.......C....~......#',
    '#.#.#.#.#.#.#.#.#~#.#',
    '#..M~C....#.#.......#',
    '#.#C#.###.#.#.#M#C#.#',
    '#.C...#..C...C....#.#',
    '#.#M#.#.#.###.###.#.#',
    '#...................#',
    '#####################',
]

LEVEL_3 = [
    '#####################',
    '#P..................#',
    '#.#.#####.#####C#.#.#',
    '#....C..#C#.C.C..C..#',
    '#.###.#.#.#.#.#.###.#',
    '#.....C...#.#...#.#.#',
    '#.###.#.###.#####.#~#',
    '#.#~...~.....C.CM..M#',
    '#.#.#.###M#.###.###M#',
    '#.#.#.........C~#...#',
    '#.#.#.###C###.#.#.#.#',
    '#..~#.....C...#.....#',
    '#####################',
]

LEVEL_4 = [
    '#####################',
    '#P#...~...C.#.......#',
    '#.###.#####.#.#####.#',
    '#...#....C....#~..#.#',
    '#.#.#C###C#.#.#.###C#',
    '#~M.#.....#M..#.....#',
    '#.#.###.#.#~###.#####',
    '#.....M.#.#.C.....CM#',
    '#.#.###.#.###~#.#.#.#',
    '#...#..CCM#.C.....#.#',
    '#C#.#.#.#.#.#######C#',
    '#.C...#.......C.....#',
    '#####################',
]

LEVEL_5 = [
    '#####################',
    '#P..C.#.C.#.......#.#',
    '#####.###.#.###.#M#.#',
    '#...#...#C..#...#.#.#',
    '#.#C###.#####.###.#.#',
    '#.#.#C..#...#M#C.C#.#',
    '#.#.#C###.#.#.#.###.#',
    '#.#...#.CM#.#.#.C..C#',
    '###.#C#.#M#.#M#####.#',
    '#....~#~#.#.#.#..M..#',
    '#.###C###.#.#.#C#####',
    '#...MC....#...#....C#',
    '#####################',
]

# The secret island, reached only by a crew holding all five map pieces.
LEVEL_SECRET = [
    '#####################',
    '#P.....C.....C.....M#',
    '#.###.###.#.###.###.#',
    '#.#C....#.C.#....C#.#',
    '#.#.###.#.#.#.###.#.#',
    '#...#C....#....C#...#',
    '###.#.#####.###.#.###',
    '#C....#..M..#.....C.#',
    '#.###.#.###.#.###.#.#',
    '#..C#...#C.....#..C.#',
    '#.#.#.#.#.###.#.#.#.#',
    '#M....C.......C....M#',
    '#####################',
]

# monster_mode: 'wander' = random movement only
#               'mix'    = wanders most of the time, occasionally chases slowly
#               'chase'  = actively chases the player
# sky:    time of day, from dawn on the first island to night on the last
# events: random perils that may strike on this island
LEVELS = [
    {"grid": LEVEL_1, "monster_mode": "wander", "monster_speed": 60,
     "name": "Driftwood Key", "sky": "dawn", "events": ["storm"],
     "lore": "Gulls circle a beach strewn with doubloons."},
    {"grid": LEVEL_2, "monster_mode": "wander", "monster_speed": 70,
     "name": "Gull's Rest", "sky": "noon", "events": ["storm", "kraken"],
     "lore": "Something large moves under the warm sand."},
    {"grid": LEVEL_3, "monster_mode": "mix", "monster_speed": 75,
     "name": "Crab Claw Atoll", "sky": "golden", "events": ["kraken", "barrage", "storm"],
     "lore": "A black sail has been seen on the horizon."},
    {"grid": LEVEL_4, "monster_mode": "mix", "monster_speed": 85,
     "name": "Smuggler's Hollow", "sky": "dusk", "events": ["barrage", "kraken", "storm"],
     "lore": "The sun sinks; the crabs grow bold."},
    {"grid": LEVEL_5, "monster_mode": "chase", "monster_speed": 100,
     "name": "Blackwater Reef", "sky": "night", "events": ["storm", "kraken", "barrage"],
     "lore": "Only your lantern lights the way now."},
]

SECRET_LEVEL = {
    "grid": LEVEL_SECRET, "monster_mode": "chase", "monster_speed": 92,
    "name": "Isla Calavera", "sky": "bloodmoon", "events": ["barrage", "kraken"],
    "lore": "The five pieces form one map. The legend is real.",
    "secret": True,
}
