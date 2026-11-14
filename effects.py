"""Atmosphere: particles, floating score text, screen shake, the living sea,
weather, time-of-day tints and the lantern-lit dark.

Everything that would be expensive per frame (full-screen alpha surfaces,
radial gradients) is built once and reused; the per-frame work is blits and a
handful of small draw calls, which matters in WebAssembly.
"""
import math
import random

import pygame

# ----------------------------------------------------------- text helpers


def outlined(font, text, fill, outline=(40, 24, 12), width=2):
    """Text with a solid outline: the cheap way to make a title read as a sign."""
    base = font.render(text, True, fill)
    edge = font.render(text, True, outline)
    w, h = base.get_width() + width * 2, base.get_height() + width * 2
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for dx in range(-width, width + 1):
        for dy in range(-width, width + 1):
            if dx * dx + dy * dy <= width * width + 1:
                surf.blit(edge, (dx + width, dy + width))
    surf.blit(base, (width, width))
    return surf


def gold_text(font, text, outline=(60, 34, 10), width=3):
    """Gold lettering with a lit upper half, for titles and big numbers."""
    top = font.render(text, True, (255, 226, 120))
    bottom = font.render(text, True, (226, 160, 40))
    h = top.get_height()
    face = pygame.Surface(top.get_size(), pygame.SRCALPHA)
    face.blit(bottom, (0, 0))
    face.blit(top, (0, 0), area=pygame.Rect(0, 0, top.get_width(), int(h * 0.52)))
    edge = font.render(text, True, outline)
    w, hh = face.get_width() + width * 2, h + width * 2 + 3
    surf = pygame.Surface((w, hh), pygame.SRCALPHA)
    surf.blit(edge, (width, width + 3))     # drop
    for dx in range(-width, width + 1):
        for dy in range(-width, width + 1):
            if dx * dx + dy * dy <= width * width + 1:
                surf.blit(edge, (dx + width, dy + width))
    surf.blit(face, (width, width))
    return surf


# --------------------------------------------------------------- particles


class Particles:
    """Small pool of short-lived dots: sparkles, sand, splashes, embers."""

    def __init__(self):
        self.items = []

    def burst(self, x, y, color, count=12, speed=120, life=0.6, gravity=200,
              size=3, spread=math.tau, angle=0.0):
        for _ in range(count):
            a = angle + random.uniform(-spread / 2, spread / 2)
            v = random.uniform(speed * 0.4, speed)
            self.items.append([x, y, math.cos(a) * v, math.sin(a) * v,
                               life * random.uniform(0.6, 1.0), life, color,
                               size, gravity])

    def update(self, dt):
        keep = []
        for p in self.items:
            p[4] -= dt
            if p[4] <= 0:
                continue
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += p[8] * dt
            p[2] *= 0.98
            keep.append(p)
        self.items = keep[-400:]

    def draw(self, surface, ox=0, oy=0):
        for x, y, _vx, _vy, t, life, color, size, _g in self.items:
            r = max(1, int(size * (t / life) + 0.5))
            pygame.draw.circle(surface, color, (int(x + ox), int(y + oy)), r)

    def clear(self):
        self.items = []


class Popups:
    """Floating "+30 x3" labels that rise and fade."""

    def __init__(self, font, font_big):
        self.font = font
        self.font_big = font_big
        self.items = []

    def add(self, x, y, text, color=(255, 230, 120), big=False, life=1.0):
        font = self.font_big if big else self.font
        surf = outlined(font, text, color, width=2)
        self.items.append([x, y, surf, life, life])

    def update(self, dt):
        for p in self.items:
            p[1] -= 38 * dt
            p[3] -= dt
        self.items = [p for p in self.items if p[3] > 0]

    def draw(self, surface, ox=0, oy=0):
        for x, y, surf, t, life in self.items:
            alpha = 255 if t > life * 0.4 else int(255 * t / (life * 0.4))
            surf.set_alpha(alpha)
            surface.blit(surf, surf.get_rect(center=(int(x + ox), int(y + oy))))

    def clear(self):
        self.items = []


class Shake:
    def __init__(self):
        self.t = 0.0
        self.power = 0.0

    def kick(self, power=8, duration=0.35):
        self.power = max(self.power, power)
        self.t = max(self.t, duration)

    def update(self, dt):
        self.t = max(0.0, self.t - dt)
        if self.t == 0:
            self.power = 0.0

    def offset(self):
        if self.t <= 0:
            return 0, 0
        p = self.power * min(1.0, self.t / 0.2)
        return random.uniform(-p, p), random.uniform(-p, p)


# -------------------------------------------------------------- the sea


class Sea:
    """Gradient water with drifting wave crests and glints. One per palette."""

    def __init__(self, size, stops, crest=(255, 255, 255), seed=0):
        from sprites import vertical_gradient
        self.w, self.h = size
        self.base = vertical_gradient(self.w, self.h, stops)
        rnd = random.Random(seed)
        self.crest = crest
        self.waves = [(rnd.uniform(0, self.w), rnd.uniform(10, self.h - 10),
                       rnd.uniform(14, 34), rnd.uniform(0, math.tau),
                       rnd.uniform(8, 22)) for _ in range(46)]
        self.t = 0.0

    def update(self, dt):
        self.t += dt

    def draw(self, surface, base=None, avoid=None):
        """`base` replaces the plain gradient (e.g. a baked scene layer) and
        crests inside `avoid` are skipped so they never ride over the land."""
        surface.blit(self.base if base is None else base, (0, 0))
        for x, y, w, ph, drift in self.waves:
            xx = (x + self.t * drift) % (self.w + 60) - 30
            k = math.sin(self.t * 1.3 + ph)
            if k < -0.2:
                continue
            yy = y + math.sin(self.t * 0.8 + ph) * 3
            if avoid is not None and avoid.collidepoint(xx, yy):
                continue
            shade = tuple(min(255, int(c)) for c in self.crest)
            rect = pygame.Rect(int(xx - w / 2), int(yy), int(w), 8)
            pygame.draw.arc(surface, shade, rect, math.pi * 0.15, math.pi * 0.85,
                            2 if k > 0.5 else 1)


# ---------------------------------------------------------- time of day


def tint_overlay(size, color, alpha):
    """A flat colour wash. Surface-wide alpha on an opaque sheet blends far
    faster than a per-pixel-alpha surface, and callers can still set_alpha."""
    surf = pygame.Surface(size)
    surf.fill(color)
    surf.set_alpha(alpha)
    return surf


class Darkness:
    """Night with a lantern: a radial hole carried by the player.

    Built from one pre-rendered light sprite plus four slices of a plain dark
    sheet around it, so nothing is allocated per frame.
    """

    def __init__(self, size, color=(8, 12, 34), alpha=215, radius=150):
        self.size = size
        self.radius = radius
        self.sheet = pygame.Surface(size, pygame.SRCALPHA)
        self.sheet.fill((*color, alpha))
        d = radius * 2
        self.light = pygame.Surface((d, d), pygame.SRCALPHA)
        self.light.fill((*color, alpha))
        steps = 36
        for i in range(steps):
            r = int(radius * (1 - i / steps))
            a = int(alpha * ((1 - i / steps) ** 1.6))
            pygame.draw.circle(self.light, (*color, a), (radius, radius), r)
        # Warm lantern tint in the middle.
        glow = pygame.Surface((d, d), pygame.SRCALPHA)
        for i in range(12):
            r = int(radius * 0.55 * (1 - i / 12))
            pygame.draw.circle(glow, (255, 170, 60, 4), (radius, radius), r)
        self.light.blit(glow, (0, 0))
        self.flicker = 0.0

    def draw(self, surface, cx, cy, t):
        w, h = self.size
        cx, cy = int(cx), int(cy)
        jitter = int(math.sin(t * 9) * 1.5 + math.sin(t * 23) * 1)
        r = self.radius + jitter
        x0, y0 = cx - r, cy - r
        x1, y1 = cx + r, cy + r
        # The four slices around the hole.
        if y0 > 0:
            surface.blit(self.sheet, (0, 0), (0, 0, w, y0))
        if y1 < h:
            surface.blit(self.sheet, (0, y1), (0, y1, w, h - y1))
        top, bottom = max(0, y0), min(h, y1)
        if bottom > top:
            if x0 > 0:
                surface.blit(self.sheet, (0, top), (0, top, x0, bottom - top))
            if x1 < w:
                surface.blit(self.sheet, (x1, top), (x1, top, w - x1, bottom - top))
        light = self.light if jitter == 0 else pygame.transform.scale(self.light, (r * 2, r * 2))
        surface.blit(light, (x0, y0))


class Rain:
    def __init__(self, size, count=140):
        self.w, self.h = size
        self.drops = [[random.uniform(0, self.w), random.uniform(0, self.h),
                       random.uniform(520, 760)] for _ in range(count)]
        self.splashes = []

    def update(self, dt, wind):
        for d in self.drops:
            d[0] += wind * 2.2 * dt
            d[1] += d[2] * dt
            if d[1] > self.h:
                if random.random() < 0.25:
                    self.splashes.append([d[0], random.uniform(80, self.h), 0.25])
                d[1] = random.uniform(-40, 0)
                d[0] = random.uniform(-60, self.w + 60)
        for s in self.splashes:
            s[2] -= dt
        self.splashes = [s for s in self.splashes if s[2] > 0][-60:]

    def draw(self, surface, wind, strength=1.0):
        n = int(len(self.drops) * strength)
        slant = wind * 0.035
        col = (190, 210, 235)
        for x, y, v in self.drops[:n]:
            pygame.draw.line(surface, col, (int(x), int(y)), (int(x - slant * 4), int(y - 14)), 1)
        for x, y, t in self.splashes:
            r = int((0.25 - t) * 28) + 1
            pygame.draw.ellipse(surface, col, (int(x - r), int(y - r / 3), r * 2, max(2, int(r * 0.66))), 1)


class Clouds:
    """Soft cloud shadows sliding across the island on fair-weather levels."""

    def __init__(self, size, alpha=26, count=4, seed=1):
        self.w, self.h = size
        rnd = random.Random(seed)
        self.items = []
        for _ in range(count):
            cw, ch = rnd.randint(160, 260), rnd.randint(70, 110)
            surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
            for _ in range(6):
                r = rnd.randint(ch // 4, ch // 2)
                pygame.draw.circle(surf, (30, 40, 60, alpha),
                                   (rnd.randint(r, cw - r), rnd.randint(r, ch - r)), r)
            self.items.append([rnd.uniform(-cw, self.w), rnd.uniform(60, self.h - ch),
                               rnd.uniform(10, 22), surf])

    def update(self, dt):
        for c in self.items:
            c[0] += c[2] * dt
            if c[0] > self.w + 20:
                c[0] = -c[3].get_width() - 20

    def draw(self, surface):
        for x, y, _v, surf in self.items:
            surface.blit(surf, (int(x), int(y)))


class Fade:
    """Fades from black whenever the scene changes."""

    def __init__(self, size):
        self.sheet = pygame.Surface(size)
        self.sheet.fill((6, 8, 16))
        self.t = 0.0
        self.dur = 0.45

    def start(self, dur=0.45):
        self.t = dur
        self.dur = dur

    def update(self, dt):
        self.t = max(0.0, self.t - dt)

    def draw(self, surface):
        if self.t > 0:
            self.sheet.set_alpha(int(255 * self.t / self.dur))
            surface.blit(self.sheet, (0, 0))
