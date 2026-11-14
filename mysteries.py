"""The secrets of each island: a buried chest with a ciphered clue, and the
random perils (storm, kraken, ghost-ship barrage) that interrupt the hunt.
"""
import math
import random

import pygame

from sprites import TILE_SIZE

NUMBERS = {1: "ONE", 2: "TWO", 3: "THREE", 4: "FOUR", 5: "FIVE"}
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def caesar(text, shift):
    out = []
    for ch in text:
        if ch in ALPHABET:
            out.append(ALPHABET[(ALPHABET.index(ch) + shift) % 26])
        else:
            out.append(ch)
    return "".join(out)


class Treasure:
    """One buried chest, located relative to a skull-shaped landmark rock.

    The clue reads e.g. "FROM THE SKULL ROCK, THREE PACES SOUTH THEN TWO WEST"
    but is shown Caesar-shifted. Collecting coins reveals letters; once enough
    are known the key (A -> ?) is shown too, so a sharp player can decode the
    rest by hand and dig early for a bonus.
    """

    KEY_AT = 0.35      # fraction of letters revealed before the key is shown

    def __init__(self, grid, rng, plain=False):
        self.found = False
        self.holes = []          # wrong digs, (col, row)
        rows, cols = len(grid), len(grid[0])
        start = next(((c, r) for r in range(rows) for c in range(cols)
                      if grid[r][c] == 'P'), (1, 1))

        walls = [(c, r) for r in range(1, rows - 1) for c in range(1, cols - 1)
                 if grid[r][c] == '#']
        spots = [(c, r) for r in range(1, rows - 1) for c in range(1, cols - 1)
                 if grid[r][c] == '.' and abs(c - start[0]) + abs(r - start[1]) >= 4]
        rng.shuffle(spots)

        choice = None
        for spot in spots:
            options = []
            for wc, wr in walls:
                dx, dy = spot[0] - wc, spot[1] - wr
                if abs(dx) <= 4 and abs(dy) <= 4 and abs(dx) + abs(dy) >= 2:
                    options.append(((wc, wr), dx, dy))
            if options:
                choice = (spot, rng.choice(options))
                break
        if choice is None:      # cannot happen on the shipped maps, but never crash
            spot = spots[0] if spots else (start[0] + 1, start[1])
            choice = (spot, ((spot[0], spot[1] - 1), 0, 1))

        (self.col, self.row), (self.landmark, dx, dy) = choice
        parts = []
        if dy:
            parts.append(f"{NUMBERS[abs(dy)]} {'SOUTH' if dy > 0 else 'NORTH'}")
        if dx:
            parts.append(f"{NUMBERS[abs(dx)]} {'EAST' if dx > 0 else 'WEST'}")
        if len(parts) == 2:
            self.plain = f"FROM THE SKULL ROCK, {parts[0]} THEN {parts[1]}"
        else:
            self.plain = f"FROM THE SKULL ROCK, {parts[0]} PACES"
        self.shift = rng.randint(3, 23)
        self.cipher = caesar(self.plain, self.shift)
        letters = [i for i, ch in enumerate(self.plain) if ch in ALPHABET]
        rng.shuffle(letters)
        self.order = letters
        self.revealed = len(letters) if plain else 0
        self.plain_mode = plain

    # ------------------------------------------------------------ reading
    @property
    def total_letters(self):
        return len(self.order)

    @property
    def hidden_letters(self):
        return self.total_letters - self.revealed

    def reveal_fraction(self, fraction):
        """Reveal letters up to `fraction` of the way (all at 85% of coins)."""
        want = math.ceil(self.total_letters * min(1.0, fraction / 0.85))
        gained = max(0, want - self.revealed)
        self.revealed = max(self.revealed, want)
        return gained

    def key_known(self):
        return self.plain_mode or self.revealed >= self.total_letters * self.KEY_AT

    def key_hint(self):
        return f"A={caesar('A', self.shift)}  ...  Z={caesar('Z', self.shift)}"

    def shown(self):
        """[(char, is_revealed)] for drawing the scroll."""
        known = set(self.order[:self.revealed])
        return [(self.plain[i] if (i in known or ch not in ALPHABET) else ch,
                 i in known or ch not in ALPHABET)
                for i, ch in enumerate(self.cipher)]

    # ------------------------------------------------------------ digging
    def dig(self, col, row):
        if self.found:
            return None
        if (col, row) == (self.col, self.row):
            self.found = True
            return True
        if (col, row) not in self.holes:
            self.holes.append((col, row))
        return False


def draw_skull_rock(surface, x, y, t=0.0):
    """The landmark: a grey boulder carved like a skull, replacing a crate."""
    s = TILE_SIZE
    cx, cy = x + s // 2, y + s // 2
    pygame.draw.ellipse(surface, (70, 64, 60), (x + 1, y + 6, s - 2, s - 2))
    pygame.draw.ellipse(surface, (150, 146, 138), (x + 2, y + 2, s - 4, s - 6))
    pygame.draw.ellipse(surface, (186, 182, 172), (x + 6, y + 4, s - 16, s - 18))
    # eye sockets
    for side in (-1, 1):
        pygame.draw.ellipse(surface, (34, 28, 30), (cx + side * 7 - 5, cy - 7, 10, 10))
    glow = int(120 + 100 * (math.sin(t * 2.5) * 0.5 + 0.5))
    for side in (-1, 1):
        pygame.draw.circle(surface, (glow, 60, 40), (cx + side * 7, cy - 2), 2)
    pygame.draw.polygon(surface, (34, 28, 30), [(cx, cy + 3), (cx - 3, cy + 8), (cx + 3, cy + 8)])
    for i in range(-2, 3):
        pygame.draw.line(surface, (90, 84, 78), (cx + i * 4, cy + 11), (cx + i * 4, cy + 15), 2)


def draw_chest(surface, cx, cy, open_k=1.0, legendary=False):
    """A treasure chest; open_k 0..1 lifts the lid and spills gold light."""
    wood = (120, 70, 30) if not legendary else (70, 30, 90)
    wood_dark = (80, 44, 16) if not legendary else (44, 16, 60)
    band = (226, 170, 50)
    body = pygame.Rect(0, 0, 30, 18)
    body.midtop = (cx, cy - 2)
    if open_k > 0:
        glow = pygame.Surface((70, 70), pygame.SRCALPHA)
        for i in range(8):
            pygame.draw.circle(glow, (255, 220, 90, int(16 * open_k)), (35, 35), 34 - i * 4)
        surface.blit(glow, (cx - 35, cy - 45))
    pygame.draw.rect(surface, wood_dark, body.move(0, 2), border_radius=4)
    pygame.draw.rect(surface, wood, body, border_radius=4)
    pygame.draw.rect(surface, band, (body.x + 4, body.y, 4, body.h))
    pygame.draw.rect(surface, band, (body.right - 8, body.y, 4, body.h))
    lid_lift = int(10 * open_k)
    lid = pygame.Rect(body.x, body.y - 10 - lid_lift, body.w, 11)
    if open_k > 0:
        pygame.draw.ellipse(surface, (255, 214, 80), (body.x + 3, body.y - 4, body.w - 6, 8))
    pygame.draw.rect(surface, wood_dark, lid.move(0, 1), border_radius=5)
    pygame.draw.rect(surface, wood, lid, border_top_left_radius=8, border_top_right_radius=8,
                     border_bottom_left_radius=2, border_bottom_right_radius=2)
    pygame.draw.rect(surface, band, (lid.centerx - 3, lid.bottom - 4, 6, 7 + lid_lift))


# ================================================================== events


class Event:
    kind = "event"
    title = ""
    banner = ""
    bonus = 0
    duration = 10.0

    def __init__(self):
        self.t = 0.0
        self.unscathed = True
        self.done = False

    @property
    def remaining(self):
        return max(0.0, self.duration - self.t)

    def update(self, dt, game):
        self.t += dt
        if self.t >= self.duration:
            self.finish()

    def finish(self):
        self.done = True

    def wind(self):
        return 0.0

    def hits(self, x, y, r):
        return False

    def draw_ground(self, surface, ox, oy):
        pass

    def draw_air(self, surface, ox, oy):
        pass


class Storm(Event):
    kind = "storm"
    title = "STORM"
    banner = "A storm rolls in!  Gold is worth double"
    bonus = 75
    duration = 14.0

    def __init__(self):
        super().__init__()
        self.wind_dir = random.choice((-1, 1))
        self.flash = 0.0
        self.next_bolt = random.uniform(1.5, 3.0)
        self.thunder_pending = []

    def strength(self):
        """Ramps in and out so the rain does not snap on and off."""
        return max(0.0, min(1.0, self.t / 1.5, (self.duration - self.t) / 1.5))

    def wind(self):
        gust = 0.6 + 0.4 * math.sin(self.t * 0.9)
        return self.wind_dir * 58 * gust * self.strength()

    def update(self, dt, game):
        super().update(dt, game)
        self.flash = max(0.0, self.flash - dt * 2.5)
        self.next_bolt -= dt
        if self.next_bolt <= 0 and self.strength() > 0.5:
            self.flash = 1.0
            self.next_bolt = random.uniform(2.2, 4.5)
            self.thunder_pending.append(random.uniform(0.2, 0.7))
            if random.random() < 0.3:
                self.wind_dir *= -1
        for i in range(len(self.thunder_pending)):
            self.thunder_pending[i] -= dt
        if any(t <= 0 for t in self.thunder_pending):
            game.sfx("thunder", 0.8)
            self.thunder_pending = [t for t in self.thunder_pending if t > 0]


class Strike:
    def __init__(self, x, y, warn):
        self.x, self.y = x, y
        self.warn = warn       # seconds of warning left
        self.age = 0.0         # seconds since impact
        self.struck = False


class StrikeEvent(Event):
    """Shared mechanics: telegraphed impacts that land near the player."""
    interval = 1.2
    warn_time = 1.1
    lethal = 0.28
    linger = 0.7
    radius = 24
    impact_sfx = "slam"
    volley = 1

    def __init__(self, open_tiles):
        super().__init__()
        self.open_tiles = open_tiles
        self.strikes = []
        self.next = 0.8

    def target(self, px, py):
        near = [(x, y) for x, y in self.open_tiles
                if abs(x - px) <= TILE_SIZE * 2.5 and abs(y - py) <= TILE_SIZE * 2.5]
        if not near:
            return px, py
        if random.random() < 0.45:
            # Aim at the player's own tile: standing still is never safe.
            return min(near, key=lambda p: (p[0] - px) ** 2 + (p[1] - py) ** 2)
        return random.choice(near)

    def update(self, dt, game):
        self.t += dt
        if self.t < self.duration - self.warn_time - 0.2:
            self.next -= dt
            if self.next <= 0:
                self.next = self.interval
                used = set()
                for _ in range(self.volley):
                    x, y = self.target(game.player.x, game.player.y)
                    if (x, y) in used:
                        continue
                    used.add((x, y))
                    self.strikes.append(Strike(x, y, self.warn_time))
                self.on_spawn(game)
        for s in self.strikes:
            if s.warn > 0:
                s.warn -= dt
                if s.warn <= 0:
                    s.struck = True
                    self.on_impact(game, s)
            else:
                s.age += dt
        self.strikes = [s for s in self.strikes if s.age < self.linger]
        if self.t >= self.duration and not self.strikes:
            self.finish()

    def on_spawn(self, game):
        pass

    def on_impact(self, game, s):
        game.sfx(self.impact_sfx, 0.7)
        game.shake.kick(5, 0.2)

    def hits(self, x, y, r):
        for s in self.strikes:
            if s.struck and s.age < self.lethal:
                if math.hypot(s.x - x, s.y - y) < self.radius + r * 0.7:
                    return True
        return False


class Kraken(StrikeEvent):
    kind = "kraken"
    title = "KRAKEN"
    banner = "The Kraken stirs beneath the sand!"
    bonus = 150
    duration = 10.0
    interval = 1.15
    warn_time = 1.15
    linger = 0.8

    def on_impact(self, game, s):
        super().on_impact(game, s)
        game.particles.burst(s.x, s.y, (230, 200, 140), count=14, speed=160, life=0.5)

    def draw_ground(self, surface, ox, oy):
        for s in self.strikes:
            cx, cy = int(s.x + ox), int(s.y + oy)
            if s.warn > 0:
                k = 1 - s.warn / self.warn_time
                r = int(8 + k * 16)
                pygame.draw.ellipse(surface, (150, 120, 80), (cx - r - 3, cy - r * 0.6 - 2, (r + 3) * 2, r * 1.2 + 4))
                pygame.draw.ellipse(surface, (40, 60, 80), (cx - r, cy - r * 0.6, r * 2, r * 1.2))
                if int(k * 10) % 2 == 0:
                    pygame.draw.ellipse(surface, (110, 60, 140), (cx - r, cy - r * 0.6, r * 2, r * 1.2), 2)
            else:
                pygame.draw.ellipse(surface, (40, 60, 80), (cx - 20, cy - 10, 40, 20))

    def draw_air(self, surface, ox, oy):
        for s in self.strikes:
            if s.warn > 0:
                continue
            k = s.age / self.linger
            height = math.sin(min(1.0, k) * math.pi) * 46 + 6
            cx, cy = s.x + ox, s.y + oy
            segs = 9
            for i in range(segs):
                f = i / (segs - 1)
                sway = math.sin(f * 3 + s.age * 8) * 6 * f
                r = int(11 - f * 7)
                px, py = int(cx + sway), int(cy - f * height)
                pygame.draw.circle(surface, (90, 40, 110), (px, py + 2), r + 1)
                pygame.draw.circle(surface, (150, 80, 170), (px, py), r)
                if i % 2 == 0 and r > 4:
                    pygame.draw.circle(surface, (236, 190, 220), (px - r // 2, py), 2)


class Barrage(StrikeEvent):
    kind = "barrage"
    title = "BARRAGE"
    banner = "A ghost ship opens fire!"
    bonus = 120
    duration = 10.0
    interval = 1.5
    warn_time = 1.4
    linger = 0.6
    lethal = 0.22
    radius = 28
    impact_sfx = "cannon"
    volley = 2

    def on_spawn(self, game):
        game.sfx("whistle", 0.5)

    def on_impact(self, game, s):
        super().on_impact(game, s)
        game.shake.kick(7, 0.25)
        game.particles.burst(s.x, s.y, (255, 170, 60), count=16, speed=200, life=0.45, gravity=0)
        game.particles.burst(s.x, s.y, (90, 84, 80), count=10, speed=80, life=0.9, gravity=-60, size=5)

    def draw_ground(self, surface, ox, oy):
        for s in self.strikes:
            cx, cy = int(s.x + ox), int(s.y + oy)
            if s.warn > 0:
                k = s.warn / self.warn_time
                r = int(10 + k * 22)
                col = (200, 40, 30) if int(s.warn * 8) % 2 == 0 else (250, 230, 200)
                pygame.draw.circle(surface, col, (cx, cy), r, 2)
                pygame.draw.line(surface, (200, 40, 30), (cx - 8, cy - 8), (cx + 8, cy + 8), 3)
                pygame.draw.line(surface, (200, 40, 30), (cx - 8, cy + 8), (cx + 8, cy - 8), 3)
            else:
                pygame.draw.ellipse(surface, (70, 52, 36), (cx - 18, cy - 10, 36, 20))

    def draw_air(self, surface, ox, oy):
        for s in self.strikes:
            cx, cy = int(s.x + ox), int(s.y + oy)
            if s.warn > 0:
                # The ball dropping in: a shrinking shadow plus the ball above it.
                k = s.warn / self.warn_time
                if k < 0.5:
                    by = cy - int(k * 2 * 220)
                    pygame.draw.circle(surface, (30, 30, 34), (cx, by), 7)
                    pygame.draw.circle(surface, (110, 110, 120), (cx - 2, by - 2), 2)
            elif s.age < 0.3:
                k = s.age / 0.3
                pygame.draw.circle(surface, (255, 220, 120), (cx, cy), int(10 + k * 26))
                pygame.draw.circle(surface, (255, 140, 40), (cx, cy), int(10 + k * 26), 4)


EVENT_TYPES = {"storm": Storm, "kraken": Kraken, "barrage": Barrage}
