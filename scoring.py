"""Points: a coin-combo multiplier and a ledger that remembers where every
point came from, so the end screen can show the breakdown.
"""

COIN_VALUE = 10
COMBO_WINDOW = 2.2           # seconds to grab the next coin and keep the chain
# Chain length at which each multiplier kicks in.
MULT_STEPS = [(10, 4), (6, 3), (3, 2), (0, 1)]

ISLAND_CLEAR = 50
UNTOUCHED = 100
CHEST = 250
EARLY_LETTER = 15            # per letter still ciphered when the chest is dug
WRONG_DIG = -5
LIFE_LEFT = 100
LEGEND = 1000

# Ledger categories in display order, with labels for the breakdown.
CATEGORIES = [
    ("coins", "Doubloons"),
    ("combo", "Combo bonus"),
    ("islands", "Islands cleared"),
    ("speed", "Swift sailing"),
    ("untouched", "Untouched islands"),
    ("treasure", "Buried chests"),
    ("cipher", "Cipher cracked early"),
    ("events", "Perils survived"),
    ("digs", "Wasted digs"),
    ("lives", "Lives remaining"),
    ("legend", "Legend of Calavera"),
]


def multiplier_for(chain):
    for need, mult in MULT_STEPS:
        if chain >= need:
            return mult
    return 1


def par_time(coins):
    """Seconds an island 'should' take; beating it earns the speed bonus."""
    return 25 + coins * 3.5


def speed_bonus(coins, elapsed):
    return max(0, int((par_time(coins) - elapsed) * 4))


class Scorer:
    def __init__(self):
        self.ledger = {key: 0 for key, _ in CATEGORIES}
        self.chain = 0
        self.timer = 0.0
        self.best_chain = 0

    @property
    def total(self):
        return sum(self.ledger.values())

    @property
    def multiplier(self):
        return multiplier_for(self.chain) if self.timer > 0 else 1

    def add(self, category, points):
        self.ledger[category] += points
        return points

    def coin(self, storm=False):
        """Bank one coin. Returns (points gained, multiplier used)."""
        self.chain = self.chain + 1 if self.timer > 0 else 1
        self.timer = COMBO_WINDOW
        self.best_chain = max(self.best_chain, self.chain)
        mult = multiplier_for(self.chain)
        base = COIN_VALUE * (2 if storm else 1)
        self.ledger["coins"] += base
        self.ledger["combo"] += base * (mult - 1)
        return base * mult, mult

    def break_chain(self):
        self.chain = 0
        self.timer = 0.0

    def update(self, dt):
        if self.timer > 0:
            self.timer = max(0.0, self.timer - dt)
            if self.timer == 0:
                self.chain = 0

    def lines(self):
        """Non-zero ledger lines for the breakdown, in display order."""
        return [(label, self.ledger[key]) for key, label in CATEGORIES if self.ledger[key]]
