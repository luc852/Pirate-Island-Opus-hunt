import asyncio
import math
import random

import pygame

import audio
import data
import levels
import scoring
import ui
from effects import (
    Particles, Popups, Shake, Sea, Darkness, Rain, Clouds, Fade,
    tint_overlay, outlined, gold_text,
)
from mysteries import (
    Treasure, EVENT_TYPES, Storm, draw_skull_rock, draw_chest, ALPHABET, caesar,
)
from sprites import (
    TILE_SIZE, Wall, Coin, Puddle, Player, Monster, MONSTER_COLORS,
    draw_sand_background, draw_heart, load_coin_frames,
    draw_pirate_avatar, vertical_gradient,
)

LOGICAL_W, LOGICAL_H = 900, 600
HUD_H = 60
FPS = 60

TITLE = "title"
INTRO = "intro"
PLAYING = "playing"
PAUSED = "paused"
LEVEL_COMPLETE = "level_complete"
GAME_OVER = "game_over"
WIN = "win"

PANEL = (255, 250, 235)
INK = (50, 40, 30)
GOLD = (222, 168, 46)
INK_SOFT = (107, 90, 72)
INK_LABEL = (138, 106, 68)
GOLD_LIT = (247, 206, 71)
GOLD_DEEP = (169, 114, 15)
PARCH = (243, 228, 188)
PARCH_DARK = (214, 190, 140)
CREAM = (246, 232, 196)
BLOOD = (170, 50, 40)
WOOD_TOP = (104, 66, 36)
WOOD_BOTTOM = (66, 40, 20)
LETTERBOX = (8, 18, 34)

SEA_STOPS = [(0.0, (79, 168, 206)), (0.42, (61, 155, 196)), (1.0, (27, 99, 137))]

# Time of day per island: sea gradient, wave-crest colour, a mood tint over
# the whole scene, whether clouds drift by, and whether it is lantern-dark.
SKIES = {
    "dawn": {"sea": [(0.0, (124, 176, 204)), (0.5, (70, 152, 192)), (1.0, (34, 98, 140))],
             "crest": (255, 236, 226), "tint": ((255, 160, 120), 26), "clouds": True},
    "noon": {"sea": SEA_STOPS, "crest": (226, 244, 252), "tint": None, "clouds": True},
    "golden": {"sea": [(0.0, (92, 160, 186)), (0.5, (52, 130, 168)), (1.0, (26, 84, 116))],
               "crest": (255, 232, 180), "tint": ((255, 176, 60), 34), "clouds": True},
    "dusk": {"sea": [(0.0, (82, 92, 150)), (0.5, (50, 74, 128)), (1.0, (20, 36, 76))],
             "crest": (236, 180, 190), "tint": ((190, 70, 110), 56), "clouds": False},
    "night": {"sea": [(0.0, (22, 44, 84)), (1.0, (6, 14, 36))],
              "crest": (120, 150, 200), "tint": None, "clouds": False,
              "dark": ((8, 12, 34), 212)},
    "bloodmoon": {"sea": [(0.0, (70, 22, 44)), (1.0, (14, 6, 22))],
                  "crest": (200, 90, 110), "tint": None, "clouds": False,
                  "dark": ((26, 4, 18), 205)},
}


def make_font(size, bold=True, serif=False):
    """Serif for headings where the system has one; the browser build falls
    back to pygame's default font for both, which is fine."""
    names = "georgia,bookantiqua,palatinolinotype,timesnewroman" if serif else "arial"
    return pygame.font.SysFont(names, size, bold=bold)


class Button:
    """A wooden plank button."""

    def __init__(self, rect, text, color=(240, 200, 90)):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.enabled = True

    def draw(self, surface, font, mouse=(-1, -1)):
        if not self.enabled:
            pygame.draw.rect(surface, (120, 104, 88), self.rect, border_radius=14)
            pygame.draw.rect(surface, (80, 66, 52), self.rect, 3, border_radius=14)
            label = font.render(self.text, True, (176, 162, 140))
            surface.blit(label, label.get_rect(center=self.rect.center))
            return
        hovered = self.rect.collidepoint(mouse)
        lift = 1 if hovered else 0
        r = self.rect.move(0, -lift)
        pygame.draw.rect(surface, (52, 30, 14), self.rect.move(0, 4), border_radius=14)
        top = (150, 96, 50) if hovered else (132, 84, 42)
        pygame.draw.rect(surface, top, r, border_radius=14)
        pygame.draw.line(surface, (104, 64, 30), (r.x + 12, r.centery), (r.right - 12, r.centery), 1)
        pygame.draw.rect(surface, (52, 30, 14), r, 3, border_radius=14)
        for nx in (r.x + 10, r.right - 10):
            pygame.draw.circle(surface, (210, 190, 150), (nx, r.y + 10), 2)
            pygame.draw.circle(surface, (210, 190, 150), (nx, r.bottom - 10), 2)
        label = outlined(font, self.text, GOLD_LIT if hovered else CREAM, (40, 22, 8), 2)
        surface.blit(label, label.get_rect(center=r.center))

    def clicked(self, pos):
        return self.enabled and self.rect.collidepoint(pos)


def draw_ship(surface, x, y, t, scale=1.0, flip=False):
    """A small galleon, bobbing on the swell."""
    bob = math.sin(t * 1.6) * 3
    tilt = math.sin(t * 1.1) * 0.05
    s = scale
    d = -1 if flip else 1

    def P(px, py):
        # rotate slightly about the hull's centre for the rocking motion
        rx = px * math.cos(tilt) - py * math.sin(tilt)
        ry = px * math.sin(tilt) + py * math.cos(tilt)
        return (x + rx * s * d, y + bob + ry * s)

    hull = [P(-48, 0), P(48, 0), P(38, 18), P(-40, 18)]
    pygame.draw.polygon(surface, (70, 40, 20), hull)
    pygame.draw.polygon(surface, (40, 22, 10), hull, 2)
    pygame.draw.line(surface, (200, 160, 60), P(-44, 6), P(44, 6), 2)
    for px in (-24, -6, 12, 30):
        pygame.draw.circle(surface, (30, 18, 8), P(px, 11), max(1, int(2 * s)))
    pygame.draw.line(surface, (60, 36, 18), P(-6, 0), P(-6, -66), max(1, int(3 * s)))
    pygame.draw.line(surface, (60, 36, 18), P(24, 0), P(24, -48), max(1, int(3 * s)))
    sail_main = [P(-30, -60), P(16, -60), P(20, -14), P(-34, -14)]
    sail_fore = [P(10, -44), P(42, -44), P(44, -10), P(8, -10)]
    for sail in (sail_main, sail_fore):
        pygame.draw.polygon(surface, (238, 226, 196), sail)
        pygame.draw.polygon(surface, (150, 130, 100), sail, 1)
    # Jolly Roger
    flag_wave = math.sin(t * 6) * 2
    flag = [P(-6, -66), P(-28, -64 + flag_wave), P(-28, -54 + flag_wave), P(-6, -56)]
    pygame.draw.polygon(surface, (20, 20, 24), flag)
    pygame.draw.circle(surface, (240, 240, 240), P(-17, -61 + flag_wave * 0.5), max(1, int(2.5 * s)))
    # wake
    for i in range(3):
        wx = -54 - i * 14
        pygame.draw.arc(surface, (240, 248, 255),
                        pygame.Rect(P(wx, 12)[0] - 8, P(wx, 12)[1], 16, 6), 0, math.pi, 1)


class Game:
    def __init__(self):
        try:
            pygame.mixer.pre_init(22050, -16, 1, 512)
        except Exception:
            pass
        pygame.init()
        pygame.display.set_caption("Pirate Island Coin Hunt")
        self.window = pygame.display.set_mode((LOGICAL_W, LOGICAL_H), pygame.RESIZABLE)
        self.surface = pygame.Surface((LOGICAL_W, LOGICAL_H))
        self.clock = pygame.time.Clock()

        self.font_small = make_font(20, bold=False)
        self.font_med = make_font(28)
        self.font_big = make_font(52, serif=True)
        self.font_title = make_font(64, serif=True)
        self.font_head = make_font(30, serif=True)
        self.font_hud = make_font(22)
        self.font_label = make_font(11)
        self.font_clue = make_font(17)
        self.font_pop = make_font(18)
        self.font_pop_big = make_font(28)

        self.shake = Shake()
        self.show_loading()
        audio.init()

        self.hud_band = self.build_hud_band()
        self.title_sea = Sea((LOGICAL_W, LOGICAL_H), SEA_STOPS, seed=3)
        self.coin_frames = load_coin_frames()
        self.coin_icon = pygame.transform.smoothscale(self.coin_frames[0], (24, 24))
        self.scores = data.load_scores()
        self.text_cache = {}

        self.particles = Particles()
        self.popups = Popups(self.font_pop, self.font_pop_big)
        self.fade = Fade((LOGICAL_W, LOGICAL_H))
        self.rain = Rain((LOGICAL_W, LOGICAL_H))
        self.dim = tint_overlay((LOGICAL_W, LOGICAL_H), (10, 8, 20), 150)
        self.flash_sheet = tint_overlay((LOGICAL_W, LOGICAL_H), (235, 240, 255), 255)
        self.storm_sheet = tint_overlay((LOGICAL_W, LOGICAL_H), (16, 26, 52), 80)

        self.running = True
        self.last_resize = None
        self.state = TITLE
        self.state_t = 0.0
        self.t = 0.0
        self.mouse = (0, 0)
        self.player_name = None
        self.save_score = True
        self.previous_best = 0
        self.level_index = 0
        self.lives = 3
        self.scorer = scoring.Scorer()
        self.shown_score = 0.0
        self.total_coins_collected = 0
        self.pieces = 0
        self.on_secret = False
        self.legend_found = False
        self.islands_cleared = 0
        self.won = False
        self.end_lines = []
        self.end_shown = 0
        self.top_rank = None

        # Title screen: pick a registered pirate, or type a fresh name.
        self.combo = ui.ComboBox((125, 226, 300, 46))
        self.name_field = ui.TextField((475, 226, 300, 46), max_len=data.MAX_NAME_LEN)
        self.save_checkbox = ui.Checkbox((475, 292), "Save my name and score", checked=True)
        self.play_button = Button((350, 486, 200, 56), "Set Sail!")
        self.refresh_roster()

        self.continue_button = Button((350, 480, 200, 55), "Continue")
        self.retry_button = Button((350, 480, 200, 55), "Play Again")

        audio.start_ambient()

    # ------------------------------------------------------------ helpers
    def show_loading(self):
        """Synthesizing the sound takes a moment, longer in a browser."""
        self.surface.fill(LETTERBOX)
        label = self.font_med.render("Hoisting the sails...", True, CREAM)
        self.surface.blit(label, label.get_rect(center=(LOGICAL_W // 2, LOGICAL_H // 2)))
        self.present()

    def sfx(self, name, volume=1.0):
        audio.play(name, volume)

    def set_state(self, state, fade=True):
        self.state = state
        self.state_t = 0.0
        if fade:
            self.fade.start()

    def cached(self, key, build):
        surf = self.text_cache.get(key)
        if surf is None:
            surf = build()
            self.text_cache[key] = surf
        return surf

    def build_hud_band(self):
        band = vertical_gradient(LOGICAL_W, HUD_H, [(0.0, WOOD_TOP), (1.0, WOOD_BOTTOM)])
        rnd = random.Random(5)
        for y in (HUD_H // 3, 2 * HUD_H // 3):
            pygame.draw.line(band, (48, 28, 12), (0, y), (LOGICAL_W, y), 1)
            pygame.draw.line(band, (124, 82, 46), (0, y + 1), (LOGICAL_W, y + 1), 1)
        for _ in range(70):
            x = rnd.randint(0, LOGICAL_W)
            y = rnd.randint(2, HUD_H - 4)
            pygame.draw.line(band, (86, 54, 28), (x, y), (x + rnd.randint(20, 80), y), 1)
        for x in range(30, LOGICAL_W, 150):
            for y in (HUD_H // 6, HUD_H // 2, 5 * HUD_H // 6):
                pygame.draw.circle(band, (40, 24, 10), (x, y), 2)
                pygame.draw.circle(band, (170, 140, 100), (x - 1, y - 1), 1)
        pygame.draw.line(band, (30, 16, 6), (0, HUD_H - 2), (LOGICAL_W, HUD_H - 2), 3)
        return band

    def parchment(self, rect, edge=(110, 74, 38)):
        """A scroll-like panel. Cached by size since the panels never move."""
        rect = pygame.Rect(rect)
        key = ("parch", rect.size)

        def build():
            w, h = rect.size
            surf = pygame.Surface((w, h + 6), pygame.SRCALPHA)
            pygame.draw.rect(surf, (40, 24, 10, 120), (0, 6, w, h), border_radius=16)
            pygame.draw.rect(surf, PARCH, (0, 0, w, h), border_radius=16)
            # pygame.draw writes alpha straight into an SRCALPHA surface rather
            # than blending, which would punch see-through holes; so the
            # aged edge and the flecks go on their own layer and are blitted.
            age = pygame.Surface((w, h), pygame.SRCALPHA)
            for i in range(10):
                a = int(70 * (1 - i / 10))
                pygame.draw.rect(age, (*PARCH_DARK, a), (i, i, w - 2 * i, h - 2 * i), 2,
                                 border_radius=max(2, 16 - i))
            surf.blit(age, (0, 0))
            rnd = random.Random(w * 31 + h)
            for _ in range(w * h // 1400):
                x, y = rnd.randint(14, w - 14), rnd.randint(14, h - 14)
                pygame.draw.circle(surf, (232, 214, 170), (x, y), rnd.randint(1, 3))
            pygame.draw.rect(surf, edge, (0, 0, w, h), 3, border_radius=16)
            return surf
        surf = self.cached(key, build)
        self.surface.blit(surf, rect.topleft)
        return rect

    def refresh_roster(self):
        self.combo.set_items(data.ranking(self.scores))

    # -------------------------------------------------------- title screen
    def chosen_name(self):
        """The name the Set Sail button would use, or "" when nothing is picked."""
        typed = data.clean_name(self.name_field.text)
        if typed:
            return data.find_player(self.scores, typed) or typed
        return self.combo.selected or ""

    def typing_new_name(self):
        return bool(data.clean_name(self.name_field.text))

    def handle_title_click(self, pos):
        action = self.combo.click(pos)
        if action:
            if action == "selected":
                # Picking from the list wins over a half-typed name.
                self.name_field.text = ""
                self.name_field.focused = False
                self.sfx("click", 0.6)
            return
        if self.name_field.click(pos):
            self.combo.selected = None
            return
        if self.typing_new_name() and self.save_checkbox.click(pos):
            return
        if self.play_button.clicked(pos):
            self.begin_from_title()

    def begin_from_title(self):
        name = self.chosen_name()
        if not name:
            return
        # An existing pirate is already on the roster; the checkbox only governs
        # whether a newly typed name gets registered.
        save = True if not self.typing_new_name() else self.save_checkbox.checked
        self.start_new_game(name, save)

    def handle_title_key(self, event):
        # Keyboard-only play: typing anywhere goes into the name field, and
        # Up/Down walks the roster, so the mouse is never required.
        ch = getattr(event, "unicode", "")
        if (not self.name_field.focused and ch and ch.isprintable() and ch != " "
                and not self.combo.open):
            self.name_field.focused = True
            self.combo.selected = None
        if self.name_field.key(event):
            if self.name_field.text:
                self.combo.selected = None
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.begin_from_title()
        elif event.key == pygame.K_ESCAPE:
            self.combo.open = False
            self.name_field.focused = False
        elif event.key in (pygame.K_UP, pygame.K_DOWN) and self.combo.items:
            names = [n for n, _ in self.combo.items]
            step = 1 if event.key == pygame.K_DOWN else -1
            if self.combo.selected in names:
                i = (names.index(self.combo.selected) + step) % len(names)
            else:
                i = 0
            self.combo.selected = names[i]
            self.name_field.text = ""
            self.name_field.focused = False
            self.sfx("click", 0.5)
        elif event.key == pygame.K_F2:
            audio.toggle_mute()

    # ---------------------------------------------------------- level setup
    def load_level(self, cfg, index):
        self.cfg = cfg
        self.on_secret = bool(cfg.get("secret"))
        grid = cfg["grid"]
        rows = len(grid)
        cols = len(grid[0])
        self.rows, self.cols = rows, cols

        self.grid_px_w = cols * TILE_SIZE
        self.grid_px_h = rows * TILE_SIZE
        self.ox = (LOGICAL_W - self.grid_px_w) // 2
        self.oy = HUD_H + (LOGICAL_H - HUD_H - self.grid_px_h) // 2

        self.bounds = pygame.Rect(0, 0, self.grid_px_w, self.grid_px_h)

        self.walls = []
        self.coins = []
        self.puddles = []
        self.monsters = []
        self.open_tiles = []
        player_start = (1, 1)

        color = MONSTER_COLORS[index % len(MONSTER_COLORS)]
        if self.on_secret:
            color = (200, 214, 230)       # ghost crabs
        for r, row in enumerate(grid):
            for c, ch in enumerate(row):
                if ch == '#':
                    self.walls.append(Wall(c, r))
                else:
                    self.open_tiles.append((c * TILE_SIZE + TILE_SIZE / 2,
                                            r * TILE_SIZE + TILE_SIZE / 2))
                if ch == 'C':
                    self.coins.append(Coin(c, r, self.coin_frames))
                elif ch == '~':
                    self.puddles.append(Puddle(c, r))
                elif ch == 'M':
                    self.monsters.append(Monster(c, r, color, cfg["monster_speed"], cfg["monster_mode"]))
                elif ch == 'P':
                    player_start = (c, r)

        self.wall_rects = [w.rect for w in self.walls]
        self.player = Player(*player_start)
        self.total_coins = len(self.coins)
        self.coins_collected_level = 0
        self.background = draw_sand_background(
            self.grid_px_w, self.grid_px_h, cols, rows, 0, 0, seed=index)

        sky = SKIES[cfg.get("sky", "noon")]
        self.sky = sky
        self.sea = Sea((LOGICAL_W, LOGICAL_H), sky["sea"], sky["crest"], seed=index)
        self.island_rect = pygame.Rect(self.ox, self.oy, self.grid_px_w, self.grid_px_h)
        self.tint = tint_overlay((LOGICAL_W, LOGICAL_H), *sky["tint"]) if sky["tint"] else None
        self.clouds = Clouds((LOGICAL_W, LOGICAL_H), seed=index) if sky["clouds"] else None
        self.dark = Darkness((LOGICAL_W, LOGICAL_H), *sky["dark"]) if sky.get("dark") else None

        self.treasure = Treasure(grid, random.Random(), plain=self.on_secret)
        self.static = self.bake_static()
        self.clue_cache_key = None
        self.chest_t = 0.0
        self.dig_cooldown = 0.0

        self.event = None
        first = 22 if index == 0 else 12
        self.event_timer = random.uniform(first, first + 8)
        self.banner = None
        self.level_t = 0.0
        self.level_hits = 0
        self.level_start_total = self.scorer.total
        self.level_summary = []
        self.legend_timer = None
        self.scorer.break_chain()      # a chain never carries across the sea
        self.particles.clear()
        self.popups.clear()
        audio.set_storm(False)

    def bake_static(self):
        """Sea, foam, sand and crates never change during an island, so they
        are composed once into a single opaque layer: one blit per frame
        instead of a hundred-odd, which is what keeps WebAssembly at 60 fps."""
        layer = self.sea.base.copy()
        island = self.island_rect
        foam = pygame.Surface((LOGICAL_W, LOGICAL_H), pygame.SRCALPHA)
        pygame.draw.rect(foam, (255, 255, 255, 34), island.inflate(28, 28), border_radius=34)
        pygame.draw.rect(foam, (255, 255, 255, 80), island.inflate(12, 12), border_radius=26)
        layer.blit(foam, (0, 0))
        layer.blit(self.background, island.topleft)
        lm = self.treasure.landmark
        for wall in self.walls:
            if (wall.rect.x // TILE_SIZE, wall.rect.y // TILE_SIZE) != lm:
                wall.draw(layer, self.ox, self.oy)
        return layer

    def start_new_game(self, player_name, save_score=True):
        self.player_name = player_name
        self.save_score = save_score
        if save_score:
            data.register_player(self.scores, player_name)
            self.refresh_roster()
        self.level_index = 0
        self.lives = 3
        self.scorer = scoring.Scorer()
        self.shown_score = 0.0
        self.total_coins_collected = 0
        self.pieces = 0
        self.islands_cleared = 0
        self.legend_found = False
        self.load_level(levels.LEVELS[0], 0)
        self.set_state(INTRO)

    def begin_island(self):
        self.set_state(PLAYING, fade=False)
        self.sfx("start", 0.8)
        self.show_banner(self.cfg["name"], self.cfg["lore"])

    # -------------------------------------------------------------- update
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            elif event.type == pygame.VIDEORESIZE:
                # Rebuild only on a genuinely new size. Calling set_mode for
                # every event makes the browser canvas oscillate: each call
                # resizes the canvas, which fires another resize, and the game
                # spends every frame re-creating the display instead of
                # reading input.
                size = (event.w, event.h)
                if size != self.window.get_size() and size != self.last_resize:
                    self.last_resize = size
                    self.window = pygame.display.set_mode(size, pygame.RESIZABLE)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.handle_click(self.to_logical_pos(event.pos))
            elif event.type == pygame.MOUSEWHEEL and self.state == TITLE:
                self.combo.wheel(self.to_logical_pos(pygame.mouse.get_pos()), event.y)
            elif event.type == pygame.KEYDOWN:
                if self.state == TITLE:
                    self.handle_title_key(event)
                else:
                    self.handle_game_key(event)

    def handle_game_key(self, event):
        key = event.key
        confirm = key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
        if key in (pygame.K_m, pygame.K_F2):
            audio.toggle_mute()
            return
        if self.state == PLAYING:
            if key in (pygame.K_SPACE, pygame.K_e):
                self.dig()
            elif key in (pygame.K_ESCAPE, pygame.K_p):
                self.set_state(PAUSED, fade=False)
        elif self.state == PAUSED:
            if key in (pygame.K_ESCAPE, pygame.K_p) or confirm:
                self.state = PLAYING
            elif key == pygame.K_q:
                audio.set_storm(False)
                self.back_to_title()
        elif self.state == INTRO:
            if self.state_t > 0.3 and (confirm or key not in (pygame.K_ESCAPE,)):
                self.begin_island()
        elif self.state == LEVEL_COMPLETE:
            if confirm and self.state_t > 0.6:
                self.advance()
        elif self.state in (GAME_OVER, WIN):
            if confirm and self.state_t > 0.8:
                if self.end_shown < len(self.end_lines):
                    self.end_shown = len(self.end_lines)   # skip the tally
                else:
                    self.back_to_title()

    def viewport(self):
        """The largest 900x600-shaped rectangle that fits, centred.

        The browser hands us a canvas of whatever shape the page is, and a
        resized desktop window is no different: scaling to fill either one
        stretches the pirates. Letterbox instead.
        """
        ww, wh = self.window.get_size()
        scale = min(ww / LOGICAL_W, wh / LOGICAL_H)
        w = max(1, int(LOGICAL_W * scale))
        h = max(1, int(LOGICAL_H * scale))
        return (ww - w) // 2, (wh - h) // 2, w, h

    def to_logical_pos(self, pos):
        ox, oy, w, h = self.viewport()
        return ((pos[0] - ox) * LOGICAL_W / w, (pos[1] - oy) * LOGICAL_H / h)

    def handle_click(self, pos):
        if self.state == TITLE:
            self.handle_title_click(pos)
        elif self.state == INTRO and self.state_t > 0.3:
            self.begin_island()
        elif self.state == LEVEL_COMPLETE:
            if self.continue_button.clicked(pos):
                self.advance()
        elif self.state in (GAME_OVER, WIN):
            if self.retry_button.clicked(pos):
                self.back_to_title()

    def back_to_title(self):
        self.name_field.text = ""
        self.name_field.focused = False
        self.combo.open = False
        self.combo.selected = self.player_name if self.save_score else None
        self.set_state(TITLE)

    def advance(self):
        """Leave a cleared island: next island, the secret one, or the end."""
        self.sfx("click", 0.6)
        if self.on_secret:
            self.finish_game(won=True)
            return
        self.level_index += 1
        if self.level_index < len(levels.LEVELS):
            self.load_level(levels.LEVELS[self.level_index], self.level_index)
            self.set_state(INTRO)
        elif self.pieces >= len(levels.LEVELS):
            self.load_level(levels.SECRET_LEVEL, len(levels.LEVELS))
            self.set_state(INTRO)
            self.sfx("legend", 0.8)
        else:
            self.finish_game(won=True)

    def finish_game(self, won):
        audio.set_storm(False)
        self.won = won
        if won and self.lives > 0:
            self.scorer.add("lives", self.lives * scoring.LIFE_LEFT)
        total = self.scorer.total
        self.previous_best = data.best_score(self.scores, self.player_name)
        self.top_rank = None
        if self.save_score:
            run = {"islands": self.islands_cleared, "chests": self.pieces,
                   "combo": self.scorer.best_chain, "legend": self.legend_found}
            self.scores = data.record_score(self.scores, self.player_name, total, run)
            self.top_rank = data.run_rank(self.scores, data.find_player(
                self.scores, self.player_name), total)
            self.refresh_roster()
        self.end_lines = self.scorer.lines()
        self.end_shown = 0
        self.end_tick = 0.0
        self.set_state(WIN if won else GAME_OVER)
        self.sfx("legend" if self.legend_found else ("win" if won else "lose"), 0.9)

    def get_keys(self):
        pressed = pygame.key.get_pressed()
        return {
            "left": pressed[pygame.K_LEFT] or pressed[pygame.K_a],
            "right": pressed[pygame.K_RIGHT] or pressed[pygame.K_d],
            "up": pressed[pygame.K_UP] or pressed[pygame.K_w],
            "down": pressed[pygame.K_DOWN] or pressed[pygame.K_s],
        }

    @property
    def score(self):
        return self.scorer.total

    def show_banner(self, text, sub="", dur=2.8):
        self.banner = [text, sub, dur, dur]

    # ------------------------------------------------------------- actions
    def dig(self):
        if self.dig_cooldown > 0 or self.treasure.found:
            return
        self.dig_cooldown = 0.45
        col = int(self.player.x // TILE_SIZE)
        row = int(self.player.y // TILE_SIZE)
        px, py = self.player.x, self.player.y + 10
        self.sfx("dig", 0.8)
        self.particles.burst(px, py, (196, 156, 96), count=10, speed=110, life=0.5,
                             gravity=260, angle=-math.pi / 2, spread=math.pi)
        result = self.treasure.dig(col, row)
        if result:
            self.chest_t = 0.0
            hidden = self.treasure.hidden_letters
            self.treasure.revealed = self.treasure.total_letters
            self.sfx("chest", 0.9)
            self.shake.kick(4, 0.25)
            self.particles.burst(px, py - 14, GOLD_LIT, count=40, speed=220, life=0.9)
            if self.on_secret:
                pts = self.scorer.add("legend", scoring.LEGEND)
                self.legend_found = True
                self.legend_timer = 2.6
                self.popups.add(px, py - 40, f"LEGENDARY TREASURE +{pts}", GOLD_LIT, big=True, life=2.4)
                self.show_banner("The Legend is Real!", "The cursed gold of Isla Calavera is yours")
                self.sfx("legend", 0.9)
            else:
                pts = self.scorer.add("treasure", scoring.CHEST)
                early = self.scorer.add("cipher", hidden * scoring.EARLY_LETTER)
                self.pieces += 1
                self.popups.add(px, py - 40, f"CHEST! +{pts}", GOLD_LIT, big=True, life=1.8)
                if early:
                    self.popups.add(px, py - 12, f"Cipher cracked early +{early}", (180, 240, 200), life=2.0)
                self.show_banner(f"Map piece {self.pieces} of {len(levels.LEVELS)}",
                                 "Collect all five to find what they lead to...")
                self.sfx("piece", 0.7)
        elif result is False:
            pts = self.scorer.add("digs", scoring.WRONG_DIG)
            self.sfx("miss", 0.6)
            self.popups.add(px, py - 30, f"Only sand {pts}", (230, 200, 170))

    def hurt(self):
        self.lives -= 1
        self.level_hits += 1
        self.player.start_invincibility()
        self.scorer.break_chain()
        if self.event:
            self.event.unscathed = False
        self.sfx("hit", 0.9)
        self.shake.kick(10, 0.4)
        self.particles.burst(self.player.x, self.player.y, (226, 75, 84), count=18, speed=180, life=0.6)
        if self.lives <= 0:
            # Dying on the secret island still means the voyage was won.
            self.finish_game(won=self.on_secret)
            return True
        return False

    def start_event(self):
        kind = random.choice(self.cfg["events"])
        cls = EVENT_TYPES[kind]
        self.event = cls() if cls is Storm else cls(self.open_tiles)
        self.show_banner(self.event.banner.split("!")[0] + "!",
                         self.event.banner.split("!", 1)[1].strip(), dur=2.4)
        self.sfx("event", 0.8)
        if kind == "kraken":
            self.sfx("kraken", 0.9)
            self.shake.kick(4, 0.8)

    def end_event(self):
        ev = self.event
        self.event = None
        audio.set_storm(False)
        if ev.unscathed and ev.done:
            pts = self.scorer.add("events", ev.bonus)
            self.popups.add(self.player.x, self.player.y - 34,
                            f"Survived the {ev.title.lower()} +{pts}", (170, 230, 255), big=True, life=1.8)
            self.sfx("piece", 0.6)
        self.event_timer = random.uniform(18, 30)

    def complete_island(self):
        if self.event:
            self.event = None
            audio.set_storm(False)
        clear = self.scorer.add("islands", scoring.ISLAND_CLEAR)
        speed = self.scorer.add("speed", scoring.speed_bonus(self.total_coins, self.level_t))
        flawless = self.scorer.add("untouched", scoring.UNTOUCHED if self.level_hits == 0 else 0)
        self.islands_cleared += 1
        self.level_summary = [
            ("Island cleared", clear),
            (f"Swift sailing ({int(self.level_t)}s)", speed),
            ("Untouched" if flawless else f"Hits taken: {self.level_hits}", flawless),
        ]
        self.sfx("clear", 0.9)
        self.set_state(LEVEL_COMPLETE, fade=False)

    def update_playing(self, dt):
        self.level_t += dt
        self.dig_cooldown = max(0.0, self.dig_cooldown - dt)
        self.scorer.update(dt)
        keys = self.get_keys()
        self.player.update(dt, keys, self.wall_rects, self.bounds)

        storm = isinstance(self.event, Storm)
        if self.event:
            wind = self.event.wind()
            if wind:
                self.player._step(wind * dt, 0, self.wall_rects, self.bounds)
            self.event.update(dt, self)
            if self.event.done:
                self.end_event()
        else:
            self.event_timer -= dt
            if self.event_timer <= 0 and self.cfg["events"]:
                self.start_event()
        audio.set_storm(isinstance(self.event, Storm))

        for coin in self.coins:
            coin.update(dt)
        for puddle in self.puddles:
            puddle.update(dt)
        for monster in self.monsters:
            monster.update(dt, self.player, self.wall_rects, self.bounds)

        for coin in self.coins:
            if not coin.collected:
                if math.hypot(coin.x - self.player.x, coin.y - self.player.y) < coin.radius + self.player.radius:
                    coin.collected = True
                    self.coins_collected_level += 1
                    self.total_coins_collected += 1
                    pts, mult = self.scorer.coin(storm=storm)
                    label = f"+{pts}" + (f"  x{mult}" if mult > 1 else "")
                    color = (255, 236, 140) if mult == 1 else (255, 170, 90)
                    self.popups.add(coin.x, coin.y - 16, label, color, big=mult >= 3)
                    self.particles.burst(coin.x, coin.y, GOLD_LIT, count=10, speed=130, life=0.45)
                    self.sfx("coin" if mult == 1 else f"coin{min(3, mult - 1)}", 0.6)
                    if not self.treasure.found:
                        had_key = self.treasure.key_known()
                        self.treasure.reveal_fraction(self.coins_collected_level / max(1, self.total_coins))
                        if not had_key and self.treasure.key_known():
                            self.popups.add(self.player.x, self.player.y - 46,
                                            "Cipher key revealed! (P to study)", (180, 240, 200), life=2.2)

        if not self.player.is_invincible:
            hit = False
            for puddle in self.puddles:
                if math.hypot(puddle.x - self.player.x, puddle.y - self.player.y) < puddle.radius + self.player.radius * 0.8:
                    hit = True
                    break
            if not hit:
                for monster in self.monsters:
                    if math.hypot(monster.x - self.player.x, monster.y - self.player.y) < monster.radius + self.player.radius:
                        hit = True
                        break
            if not hit and self.event and self.event.hits(self.player.x, self.player.y, self.player.radius):
                hit = True
            if hit and self.hurt():
                return

        if self.treasure.found:
            self.chest_t += dt
        if self.legend_timer is not None:
            self.legend_timer -= dt
            if self.legend_timer <= 0:
                self.legend_timer = None
                self.islands_cleared += 1
                self.finish_game(won=True)
                return

        if (not self.on_secret and self.coins_collected_level >= self.total_coins
                and self.total_coins > 0):
            self.complete_island()

    def update(self, dt):
        self.t += dt
        self.state_t += dt
        self.mouse = self.to_logical_pos(pygame.mouse.get_pos())
        self.fade.update(dt)
        self.shake.update(dt)
        if self.state == PLAYING:
            self.update_playing(dt)
        if self.state in (PLAYING, LEVEL_COMPLETE, INTRO):
            self.sea.update(dt)
            if self.clouds:
                self.clouds.update(dt)
            self.particles.update(dt)
            self.popups.update(dt)
            if self.banner:
                self.banner[2] -= dt
                if self.banner[2] <= 0:
                    self.banner = None
            if isinstance(self.event, Storm):
                self.rain.update(dt, self.event.wind())
        elif self.state == TITLE:
            self.title_sea.update(dt)
            self.name_field.update(dt)
        elif self.state in (GAME_OVER, WIN):
            self.title_sea.update(dt)
            self.particles.update(dt)
            if self.end_shown < len(self.end_lines):
                self.end_tick += dt
                if self.end_tick > 0.32 and self.state_t > 0.6:
                    self.end_tick = 0.0
                    self.end_shown += 1
                    self.sfx("tick", 0.8)
            if self.legend_found and random.random() < 0.3:
                self.particles.burst(random.uniform(0, LOGICAL_W), -5, GOLD_LIT, count=1,
                                     speed=40, life=3.0, gravity=60, size=3)
        # The HUD score rolls up rather than jumping.
        target = self.scorer.total
        self.shown_score += (target - self.shown_score) * min(1.0, dt * 8)
        if abs(target - self.shown_score) < 0.5:
            self.shown_score = float(target)

    # ---------------------------------------------------------------- draw
    def draw_hud(self):
        mid = HUD_H // 2
        s = self.surface
        s.blit(self.hud_band, (0, 0))
        x = 14

        # Island chip
        cap = self.font_label.render("ISLAND", True, (214, 180, 120))
        if self.on_secret:
            num = self.font_hud.render("??", True, (255, 120, 120))
            den = self.font_small.render("", True, CREAM)
        else:
            num = self.font_hud.render(f"{self.level_index + 1}", True, CREAM)
            den = self.font_small.render(f"/{len(levels.LEVELS)}", True, (190, 160, 120))
        pill_w = 12 + cap.get_width() + 8 + num.get_width() + den.get_width() + 12
        pill = pygame.Rect(x, mid - 17, pill_w, 34)
        pygame.draw.rect(s, (36, 22, 10), pill, border_radius=17)
        pygame.draw.rect(s, (150, 110, 60), pill, 2, border_radius=17)
        s.blit(cap, cap.get_rect(midleft=(pill.x + 12, mid)))
        s.blit(num, num.get_rect(midleft=(pill.x + 12 + cap.get_width() + 8, mid)))
        s.blit(den, den.get_rect(bottomleft=(pill.x + 12 + cap.get_width() + 8 + num.get_width(), mid + 10)))
        x = pill.right + 16

        for i in range(3):
            draw_heart(s, x + 13 + i * 30, mid, 25, filled=i < self.lives)
        x += 3 * 30 + 10

        # Coins and how much of the island is left
        s.blit(self.coin_icon, self.coin_icon.get_rect(center=(x + 12, mid)))
        x += 30
        found = self.font_hud.render(f"{self.coins_collected_level}", True, CREAM)
        total = self.font_small.render(f"/{self.total_coins}", True, (200, 170, 120))
        s.blit(found, (x, mid - 18))
        s.blit(total, (x + found.get_width(), mid - 12))
        track = pygame.Rect(x, mid + 8, 80, 6)
        pygame.draw.rect(s, (40, 24, 10), track, border_radius=3)
        if self.total_coins:
            filled = int(track.width * self.coins_collected_level / self.total_coins)
            if filled > 0:
                pygame.draw.rect(s, GOLD_LIT, (track.x, track.y, filled, track.height), border_radius=3)
        x = track.right + 16

        # Map pieces
        cap = self.font_label.render("MAP", True, (214, 180, 120))
        s.blit(cap, (x, mid - 18))
        for i in range(len(levels.LEVELS)):
            r = pygame.Rect(x + i * 15, mid - 3, 12, 14)
            got = i < self.pieces
            pygame.draw.rect(s, PARCH if got else (60, 38, 20), r, border_radius=2)
            pygame.draw.rect(s, (150, 110, 60), r, 1, border_radius=2)
            if got:
                pygame.draw.line(s, BLOOD, (r.x + 3, r.y + 4), (r.right - 4, r.bottom - 4), 2)
                pygame.draw.line(s, BLOOD, (r.x + 3, r.bottom - 4), (r.right - 4, r.y + 4), 2)
        x += len(levels.LEVELS) * 15 + 14

        # Active peril, centre
        if self.event:
            label = f"{self.event.title}  {int(math.ceil(self.event.remaining))}s"
            chip_txt = self.font_hud.render(label, True, (255, 230, 200))
            chip = chip_txt.get_rect(midleft=(x + 6, mid)).inflate(20, 10)
            pulse = int(140 + 60 * math.sin(self.t * 6))
            pygame.draw.rect(s, (pulse, 40, 30), chip, border_radius=10)
            pygame.draw.rect(s, (40, 10, 6), chip, 2, border_radius=10)
            s.blit(chip_txt, chip_txt.get_rect(center=chip.center))

        # Right edge: score, then combo badge to its left.
        rx = LOGICAL_W - 16
        who = (self.player_name or "").upper()
        cap = self.font_label.render(f"{who}'S PLUNDER" if who else "PLUNDER", True, (214, 180, 120))
        shown = int(round(self.shown_score))
        if getattr(self, "_score_key", None) != shown:
            self._score_key = shown
            self._score_surf = gold_text(self.font_med, str(shown), width=2)
        val = self._score_surf
        s.blit(cap, cap.get_rect(topright=(rx, 5)))
        s.blit(val, val.get_rect(topright=(rx + 2, 17)))
        rx -= max(cap.get_width(), val.get_width()) + 26

        mult = self.scorer.multiplier
        cx = rx - 20
        pygame.draw.circle(s, (36, 22, 10), (cx, mid), 21)
        if self.scorer.timer > 0:
            frac = self.scorer.timer / scoring.COMBO_WINDOW
            pygame.draw.arc(s, GOLD_LIT if mult > 1 else (200, 170, 120),
                            (cx - 21, mid - 21, 42, 42), math.pi / 2, math.pi / 2 + frac * math.tau, 4)
        col = [(160, 130, 100), CREAM, GOLD_LIT, (255, 150, 70), (255, 90, 70)][mult]
        txt = self.font_hud.render(f"x{mult}", True, col)
        s.blit(txt, txt.get_rect(center=(cx, mid)))
        if self.scorer.chain > 1:
            ch = self.font_label.render(f"{self.scorer.chain} CHAIN", True, (214, 180, 120))
            s.blit(ch, ch.get_rect(midright=(cx - 26, mid)))

    def draw_clue(self):
        """The ciphered clue, painted on a scroll over the bottom border wall."""
        tr = self.treasure
        rect = pygame.Rect(self.ox + 6, self.oy + (self.rows - 1) * TILE_SIZE + 4,
                           self.grid_px_w - 12, TILE_SIZE - 8)
        key = (tr.revealed, tr.found, self.pieces, tr.key_known())
        if key != self.clue_cache_key:
            self.clue_cache_key = key
            surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(surf, (*PARCH, 245), surf.get_rect(), border_radius=6)
            pygame.draw.rect(surf, (110, 74, 38), surf.get_rect(), 2, border_radius=6)
            for end in (0, rect.w - 10):
                pygame.draw.rect(surf, (150, 110, 60), (end, 0, 10, rect.h), border_radius=4)
            x = 18
            cy = rect.h // 2
            if tr.found:
                if self.on_secret:
                    msg = "THE LEGENDARY CHEST IS YOURS!"
                else:
                    msg = f"CHEST UNEARTHED - MAP PIECE {self.pieces} OF {len(levels.LEVELS)}"
                t = self.font_clue.render(msg, True, (40, 110, 50))
                surf.blit(t, t.get_rect(center=(rect.w // 2, cy)))
            else:
                lab = self.font_label.render("LEGEND" if self.on_secret else "CLUE", True, BLOOD)
                surf.blit(lab, lab.get_rect(midleft=(x, cy)))
                x += lab.get_width() + 10
                for ch, known in tr.shown():
                    color = INK if known else (176, 60, 44)
                    g = self.font_clue.render(ch, True, color)
                    if not known:
                        pygame.draw.line(surf, (200, 150, 120), (x, cy + 10), (x + g.get_width(), cy + 10), 1)
                    surf.blit(g, g.get_rect(midleft=(x, cy)))
                    x += g.get_width() + (1 if ch != " " else 2)
                if tr.key_known() and not self.on_secret:
                    k = self.font_label.render(f"KEY  {tr.key_hint()}", True, (40, 110, 50))
                    surf.blit(k, k.get_rect(midright=(rect.w - 18, cy)))
                elif not self.on_secret:
                    hint = self.font_label.render("DOUBLOONS DECIPHER", True, INK_LABEL)
                    surf.blit(hint, hint.get_rect(midright=(rect.w - 18, cy)))
            self.clue_surf = surf
        self.surface.blit(self.clue_surf, rect.topleft)

    def draw_banner(self):
        if not self.banner:
            return
        text, sub, t, dur = self.banner
        k = min(1.0, (dur - t) / 0.3, t / 0.4)
        y = int(HUD_H + 26 + (1 - k) * -40)
        title = self.cached(("banner", text), lambda: gold_text(self.font_head, text, width=3))
        w = max(title.get_width(), 200) + 80
        if sub:
            sub_s = self.cached(("bsub", sub), lambda: outlined(self.font_small, sub, CREAM, (30, 16, 6), 2))
            w = max(w, sub_s.get_width() + 60)
        rect = pygame.Rect(0, 0, w, 74 if sub else 50)
        rect.midtop = (LOGICAL_W // 2, y)
        ribbon = pygame.Surface(rect.size, pygame.SRCALPHA)
        ribbon.fill((30, 16, 8, 200))
        pygame.draw.rect(ribbon, (200, 150, 70, 255), ribbon.get_rect(), 2)
        ribbon.set_alpha(int(255 * max(0.0, k)))
        self.surface.blit(ribbon, rect)
        self.surface.blit(title, title.get_rect(midtop=(rect.centerx, rect.y + 4)))
        if sub:
            self.surface.blit(sub_s, sub_s.get_rect(midtop=(rect.centerx, rect.y + 46)))

    def draw_playing(self):
        s = self.surface
        ox, oy = self.ox, self.oy
        self.sea.draw(s, self.static, self.island_rect.inflate(40, 40))
        pulse = int((math.sin(self.t * 1.6) * 0.5 + 0.5) * 6)
        pygame.draw.rect(s, (236, 246, 250), self.island_rect.inflate(14 + pulse, 14 + pulse), 2,
                         border_radius=27 + pulse // 2)
        tr = self.treasure
        for c, r in tr.holes:
            pygame.draw.ellipse(s, (170, 128, 80), (ox + c * TILE_SIZE + 9, oy + r * TILE_SIZE + 16, 22, 11))
            pygame.draw.ellipse(s, (120, 86, 50), (ox + c * TILE_SIZE + 11, oy + r * TILE_SIZE + 18, 18, 7))
        lm = tr.landmark
        draw_skull_rock(s, lm[0] * TILE_SIZE + ox, lm[1] * TILE_SIZE + oy, self.t)
        for puddle in self.puddles:
            puddle.draw(s, ox, oy)
        if tr.found:
            draw_chest(s, ox + tr.col * TILE_SIZE + TILE_SIZE // 2, oy + tr.row * TILE_SIZE + TILE_SIZE // 2 + 4,
                       min(1.0, self.chest_t / 0.6), legendary=self.on_secret)
        if self.event and not self.dark:
            self.event.draw_ground(s, ox, oy)
        for coin in self.coins:
            coin.draw(s, ox, oy)
        for monster in self.monsters:
            monster.draw(s, ox, oy)
        self.player.draw(s, ox, oy)
        if self.event and not self.dark:
            self.event.draw_air(s, ox, oy)
        self.particles.draw(s, ox, oy)

        if self.clouds:
            self.clouds.draw(s)
        if isinstance(self.event, Storm):
            st = self.event.strength()
            if not self.dark:       # at night the dark already does this job
                self.storm_sheet.set_alpha(int(80 * st))
                s.blit(self.storm_sheet, (0, 0))
            self.rain.draw(s, self.event.wind(), st)
        if self.tint:
            s.blit(self.tint, (0, 0))
        if self.dark:
            self.dark.draw(s, self.player.x + ox, self.player.y + oy, self.t)
            # What a lantern can't hide: glinting gold, glowing eyes, and
            # every telegraphed strike (hiding those would be unfair).
            for coin in self.coins:
                if not coin.collected and math.sin(self.t * 3 + coin.anim_t) > 0.3:
                    pygame.draw.circle(s, (255, 220, 120), (int(coin.x + ox), int(coin.y + oy)), 2)
            for m in self.monsters:
                for side in (-1, 1):
                    pygame.draw.circle(s, (255, 230, 90), (int(m.x + ox + side * 5), int(m.y + oy - 12)), 2)
            if tr.found:
                draw_chest(s, ox + tr.col * TILE_SIZE + TILE_SIZE // 2,
                           oy + tr.row * TILE_SIZE + TILE_SIZE // 2 + 4, 1.0, legendary=self.on_secret)
            lx, ly = lm
            for side in (-1, 1):
                pygame.draw.circle(s, (255, 80, 50), (ox + lx * TILE_SIZE + 20 + side * 7, oy + ly * TILE_SIZE + 18), 2)
            if self.event:
                self.event.draw_ground(s, ox, oy)
                self.event.draw_air(s, ox, oy)
        if isinstance(self.event, Storm) and self.event.flash > 0:
            self.flash_sheet.set_alpha(int(170 * self.event.flash))
            s.blit(self.flash_sheet, (0, 0))
        self.popups.draw(s, ox, oy)
        self.draw_clue()
        self.draw_banner()
        self.draw_hud()

    def draw_title(self):
        s = self.surface
        self.title_sea.draw(s)
        draw_ship(s, (self.t * 22 + 140) % (LOGICAL_W + 240) - 120, 552, self.t, 0.8)

        title = self.cached("title", lambda: gold_text(self.font_title, "Pirate Island Coin Hunt", width=4))
        s.blit(title, title.get_rect(center=(LOGICAL_W // 2, 54)))

        self.draw_best_banner(118)

        self.parchment((100, 160, 700, 300))

        head_left = self.font_med.render("Returning pirate", True, INK)
        s.blit(head_left, head_left.get_rect(midleft=(125, 192)))
        head_right = self.font_med.render("New pirate", True, INK)
        s.blit(head_right, head_right.get_rect(midleft=(475, 192)))

        pygame.draw.line(s, PARCH_DARK, (450, 185), (450, 435), 2)
        or_chip = pygame.Rect(0, 0, 40, 28)
        or_chip.center = (450, 300)
        pygame.draw.rect(s, PARCH, or_chip)
        or_label = self.font_small.render("or", True, INK_LABEL)
        s.blit(or_label, or_label.get_rect(center=or_chip.center))

        typing = self.typing_new_name()
        self.combo.draw(s, self.font_med, self.font_small, active=not typing)
        self.name_field.draw(s, self.font_med, active=True)
        self.save_checkbox.draw(s, self.font_small, active=typing)

        if typing:
            typed = data.clean_name(self.name_field.text)
            match = data.find_player(self.scores, typed)
            if match:
                hint = f"Joins {match} (best {data.best_score(self.scores, match)})"
                color = (60, 130, 80)
            elif self.save_checkbox.checked:
                hint = "New pirate - will join the roster"
                color = INK_LABEL
            else:
                hint = "Guest run - nothing will be saved"
                color = (170, 90, 60)
            note = self.font_small.render(hint, True, color)
            s.blit(note, note.get_rect(midleft=(475, 336)))
        else:
            note = self.font_small.render(
                f"{len(self.combo.items)} pirate(s) registered", True, INK_LABEL)
            s.blit(note, note.get_rect(midleft=(125, 292)))
            if self.combo.selected:
                e = data.player_entry(self.scores, self.combo.selected)
                rec = f"Best chain {e.get('best_combo', 0)}  -  chests {e.get('chests', 0)}/5"
                s.blit(self.font_small.render(rec, True, INK_SOFT), (125, 318))
                if e.get("legend"):
                    leg = self.font_small.render("Found the Legend of Calavera!", True, GOLD_DEEP)
                    s.blit(leg, (125, 344))

        # How to play, in the panel's lower band.
        tips = ["Grab doubloons fast to chain combos up to x4",
                "Each doubloon deciphers the clue - SPACE digs up the chest",
                "Five chests make a map... to somewhere"]
        for i, tip in enumerate(tips):
            t = self.font_small.render(tip, True, INK_SOFT)
            s.blit(t, t.get_rect(midleft=(140, 380 + i * 24)))
            pygame.draw.circle(s, BLOOD, (128, 380 + i * 24), 4)

        self.play_button.enabled = bool(self.chosen_name())
        self.play_button.draw(s, self.font_med, self.mouse)

        sound = "sound off" if not audio.is_muted() else "sound on"
        hint = self.font_small.render(
            f"Type a name or Up/Down to pick - Enter to set sail - M ({sound}) in game, F2 here",
            True, (226, 240, 248))
        s.blit(hint, hint.get_rect(center=(LOGICAL_W // 2, 580)))

        # Last, so the open list floats over the panel and the button.
        self.combo.draw_list(s, self.font_small, self.mouse)

    def draw_best_banner(self, cy):
        best = self.scores["overall_best"]
        if best["name"]:
            text = f"Best pirate: {best['name']} - {best['score']} points"
        else:
            text = "No treasure claimed yet - be the first!"
        label = self.font_med.render(text, True, INK)
        chip = label.get_rect(center=(LOGICAL_W // 2, cy)).inflate(96, 18)
        ui.shadowed_box(self.surface, chip, (255, 233, 176), radius=chip.height // 2,
                        edge=GOLD_DEEP, width=3)
        self.surface.blit(self.coin_icon,
                          self.coin_icon.get_rect(midleft=(chip.x + 16, cy)))
        self.surface.blit(label, label.get_rect(center=(LOGICAL_W // 2, cy)))

    def draw_intro(self):
        self.draw_playing()
        s = self.surface
        s.blit(self.dim, (0, 0))
        panel = self.parchment((LOGICAL_W // 2 - 300, 120, 600, 380))
        if self.on_secret:
            cap = "THE SECRET ISLAND"
        else:
            cap = f"ISLAND {self.level_index + 1} OF {len(levels.LEVELS)}"
        c = self.font_label.render(cap, True, BLOOD)
        s.blit(c, c.get_rect(center=(panel.centerx, panel.y + 30)))
        name = self.cached(("iname", self.cfg["name"]), lambda: gold_text(self.font_big, self.cfg["name"], width=3))
        s.blit(name, name.get_rect(center=(panel.centerx, panel.y + 74)))
        lore = self.font_small.render(self.cfg["lore"], True, INK_SOFT)
        s.blit(lore, lore.get_rect(center=(panel.centerx, panel.y + 120)))

        if self.on_secret:
            lines = ["Your five map pieces fit together into one chart.",
                     "The legend is written plain - no cipher this time.",
                     "Dig up the Legendary Chest to claim the secret ending.",
                     "Doubloons here are a bonus. The ghosts hunt in the dark."]
        elif self.level_index == 0:
            lines = ["Collect every doubloon to leave the island.",
                     "Each doubloon deciphers the clue on the scroll below.",
                     "Stand on the spot and press SPACE to dig up the chest -",
                     "but do it before the last doubloon, or it stays buried!",
                     "Chain doubloons quickly for up to x4 points."]
        else:
            perils = ", ".join(e.title() if e != "barrage" else "Ghost ship" for e in self.cfg["events"])
            lines = [f"Perils sighted: {perils}.",
                     "Survive a peril untouched for a bonus.",
                     "Crack the cipher by hand and dig early for extra gold.",
                     f"Map pieces found: {self.pieces} of {len(levels.LEVELS)}."]
        for i, line in enumerate(lines):
            t = self.cached(("intro", line), lambda: self.font_small.render(line, True, INK))
            s.blit(t, t.get_rect(center=(panel.centerx, panel.y + 170 + i * 30)))
        if int(self.t * 2) % 2 == 0 or self.state_t < 0.3:
            go = self.font_med.render("Press any key to land", True, BLOOD)
            s.blit(go, go.get_rect(center=(panel.centerx, panel.bottom - 34)))

    def draw_paused(self):
        self.draw_playing()
        s = self.surface
        s.blit(self.dim, (0, 0))
        panel = self.parchment((LOGICAL_W // 2 - 330, 110, 660, 400))
        head = self.cached("paused", lambda: gold_text(self.font_big, "Ship's Log", width=3))
        s.blit(head, head.get_rect(center=(panel.centerx, panel.y + 46)))
        tr = self.treasure
        y = panel.y + 100
        lab = self.font_label.render("THE CLUE AS YOU HAVE IT", True, BLOOD)
        s.blit(lab, lab.get_rect(center=(panel.centerx, y)))
        shown = "".join(ch for ch, _ in tr.shown())
        t = self.font_clue.render(shown if not tr.found else tr.plain, True, INK)
        s.blit(t, t.get_rect(center=(panel.centerx, y + 26)))
        y += 64
        if tr.key_known() and not tr.found:
            lab = self.font_label.render("DECODER  (cipher letter above, true letter below)", True, BLOOD)
            s.blit(lab, lab.get_rect(center=(panel.centerx, y)))
            cw = 22
            x0 = panel.centerx - cw * 13
            for i, plain in enumerate(ALPHABET):
                cx = x0 + i * cw + cw // 2
                a = self.font_clue.render(caesar(plain, tr.shift), True, (176, 60, 44))
                b = self.font_clue.render(plain, True, INK)
                s.blit(a, a.get_rect(center=(cx, y + 24)))
                s.blit(b, b.get_rect(center=(cx, y + 48)))
            y += 80
        elif not tr.found:
            msg = "Collect more doubloons to learn the cipher key."
            m = self.font_small.render(msg, True, INK_SOFT)
            s.blit(m, m.get_rect(center=(panel.centerx, y + 10)))
            y += 40
        controls = ["Arrows/WASD move  -  SPACE/E dig  -  M sound",
                    "P or Enter: resume  -  Q: abandon (not saved)"]
        for i, line in enumerate(controls):
            c = self.font_small.render(line, True, INK_SOFT)
            s.blit(c, c.get_rect(center=(panel.centerx, panel.bottom - 70 + i * 28)))

    def draw_level_complete(self):
        self.draw_playing()
        s = self.surface
        s.blit(self.dim, (0, 0))
        panel = self.parchment((LOGICAL_W // 2 - 280, 120, 560, 410))
        title = self.cached("cleared", lambda: gold_text(self.font_big, "Island Cleared!", width=3))
        s.blit(title, title.get_rect(center=(panel.centerx, panel.y + 48)))
        name = self.font_small.render(self.cfg["name"], True, INK_SOFT)
        s.blit(name, name.get_rect(center=(panel.centerx, panel.y + 92)))

        y = panel.y + 124
        rows = list(self.level_summary)
        if self.treasure.found:
            rows.append(("Buried chest found", None))
        else:
            rows.append(("The chest stays buried...", None))
        for i, (label, pts) in enumerate(rows):
            if self.state_t < 0.25 * (i + 1):
                break
            color = INK if (pts or pts is None and self.treasure.found) else INK_LABEL
            l = self.font_small.render(label, True, color)
            s.blit(l, (panel.x + 50, y))
            if pts is not None:
                v = self.font_med.render(f"+{pts}" if pts else "-", True, GOLD_DEEP if pts else INK_LABEL)
                s.blit(v, v.get_rect(topright=(panel.right - 50, y - 4)))
            y += 34

        island_total = self.scorer.total - self.level_start_total
        pygame.draw.line(s, PARCH_DARK, (panel.x + 40, y + 2), (panel.right - 40, y + 2), 2)
        t = self.font_med.render(f"This island: {island_total}", True, INK)
        s.blit(t, (panel.x + 50, y + 12))
        tot = self.font_med.render(f"Total {self.scorer.total}", True, BLOOD)
        s.blit(tot, tot.get_rect(topright=(panel.right - 50, y + 12)))

        # Lives and map pieces
        y += 62
        for i in range(3):
            draw_heart(s, panel.x + 70 + i * 30, y + 10, 22, filled=i < self.lives)
        for i in range(len(levels.LEVELS)):
            r = pygame.Rect(panel.right - 60 - (len(levels.LEVELS) - i) * 26, y, 22, 24)
            got = i < self.pieces
            pygame.draw.rect(s, (250, 240, 210) if got else PARCH_DARK, r, border_radius=3)
            pygame.draw.rect(s, (110, 74, 38), r, 2, border_radius=3)
            if got:
                pygame.draw.line(s, BLOOD, (r.x + 6, r.y + 6), (r.right - 7, r.bottom - 7), 3)
                pygame.draw.line(s, BLOOD, (r.x + 6, r.bottom - 7), (r.right - 7, r.y + 6), 3)

        last = self.level_index + 1 >= len(levels.LEVELS) and not self.on_secret
        if last and self.pieces >= len(levels.LEVELS):
            self.continue_button.text = "Follow the map"
        elif last:
            self.continue_button.text = "Sail home"
        else:
            self.continue_button.text = "Set sail"
        self.continue_button.rect = pygame.Rect(0, 0, 230, 52)
        self.continue_button.rect.midtop = (LOGICAL_W // 2, panel.bottom + 4)
        self.continue_button.draw(s, self.font_med, self.mouse)

    def draw_end_screen(self, won):
        s = self.surface
        legend = self.legend_found
        self.title_sea.draw(s)
        s.blit(self.dim, (0, 0))
        if legend:
            glow = self.cached("legendglow", lambda: tint_overlay((LOGICAL_W, LOGICAL_H), (255, 190, 60), 40))
            s.blit(glow, (0, 0))
            self.particles.draw(s)

        if legend:
            head, sub = "Legend of Isla Calavera", "You found the treasure every pirate swore was a myth."
        elif won:
            head = "You win, matey!"
            sub = "Every island plundered." + ("" if self.pieces >= len(levels.LEVELS) else
                                              f"  Yet {len(levels.LEVELS) - self.pieces} chest(s) stay buried... legend speaks of more.")
        else:
            head, sub = "Game Over", "Davy Jones takes another. Take a breath and try again!"
        title = self.cached(("end", head), lambda: gold_text(self.font_big, head, width=3))
        s.blit(title, title.get_rect(center=(LOGICAL_W // 2, 46)))
        sub_s = self.font_small.render(sub, True, CREAM)
        s.blit(sub_s, sub_s.get_rect(center=(LOGICAL_W // 2, 92)))

        # Left: the breakdown, tallied one line at a time.
        left = self.parchment((40, 118, 420, 400))
        cap = self.font_label.render(f"{(self.player_name or '').upper()}'S PLUNDER", True, BLOOD)
        s.blit(cap, (left.x + 24, left.y + 18))
        y = left.y + 38
        shown_total = 0
        for label, pts in self.end_lines[:self.end_shown]:
            l = self.font_small.render(label, True, INK)
            s.blit(l, (left.x + 24, y))
            v = self.font_small.render(f"{pts:+d}", True, GOLD_DEEP if pts > 0 else BLOOD)
            s.blit(v, v.get_rect(topright=(left.right - 24, y)))
            shown_total += pts
            y += 22
        if not self.end_lines:
            s.blit(self.font_small.render("Not a single doubloon...", True, INK_LABEL), (left.x + 24, y))
        done = self.end_shown >= len(self.end_lines)
        ty = left.bottom - 108
        pygame.draw.line(s, PARCH_DARK, (left.x + 20, ty), (left.right - 20, ty), 2)
        total_s = gold_text(self.font_big, str(self.score if done else shown_total), width=3)
        s.blit(total_s, total_s.get_rect(midright=(left.right - 22, ty + 36)))
        s.blit(self.font_med.render("Total", True, INK), (left.x + 24, ty + 20))
        if done:
            if self.save_score:
                best = data.best_score(self.scores, self.player_name)
                note = f"Your best: {best}"
                color = INK_SOFT
                if self.score > self.previous_best:
                    note = "New personal record!"
                    color = (40, 120, 50)
            else:
                note, color = "Guest run - this score was not saved", (150, 90, 60)
            n = self.font_small.render(note, True, color)
            s.blit(n, (left.x + 24, ty + 60))
            if self.save_score and self.top_rank:
                r = self.font_small.render(f"Voyage #{self.top_rank} in the Hall of Fame", True, GOLD_DEEP)
                s.blit(r, (left.x + 24, ty + 82))

        # Right: the ten best voyages.
        self.draw_hall_of_fame(pygame.Rect(480, 118, 380, 400))

        self.retry_button.rect = pygame.Rect(0, 0, 230, 52)
        self.retry_button.rect.midtop = (LOGICAL_W // 2, 534)
        self.retry_button.text = "Back to Title"
        self.retry_button.draw(s, self.font_med, self.mouse)

    def draw_hall_of_fame(self, rect):
        s = self.surface
        panel = self.parchment(rect)
        head = self.cached("hof", lambda: gold_text(self.font_head, "Hall of Fame", width=2))
        s.blit(head, head.get_rect(midtop=(panel.centerx, panel.y + 10)))
        for label, x, right in (("PIRATE", 50, False), ("SCORE", 240, True),
                                ("CHESTS", 292, True), ("CHAIN", 344, True)):
            c = self.font_label.render(label, True, INK_LABEL)
            pos = c.get_rect(topright=(panel.x + x, panel.y + 56)) if right else                 c.get_rect(topleft=(panel.x + x, panel.y + 56))
            s.blit(c, pos)
        runs = self.scores.get("runs", [])
        if not runs:
            e = self.font_small.render("No voyages recorded yet.", True, INK_LABEL)
            s.blit(e, e.get_rect(center=(panel.centerx, panel.centery)))
            return
        y = panel.y + 74
        for i, r in enumerate(runs[:10]):
            mine = self.top_rank == i + 1 and self.save_score
            if mine:
                pygame.draw.rect(s, (250, 220, 150), (panel.x + 12, y - 2, panel.w - 24, 30), border_radius=6)
            color = BLOOD if mine else INK
            rank = self.font_small.render(f"{i + 1}.", True, INK_LABEL)
            s.blit(rank, (panel.x + 18, y + 2))
            name = self.font_small.render(r["name"], True, GOLD_DEEP if r.get("legend") else color)
            s.blit(name, (panel.x + 50, y + 2))
            if r.get("legend"):
                cx, cy = panel.x + 56 + name.get_width() + 10, y + 12
                pygame.draw.polygon(s, GOLD, [(cx - 8, cy + 6), (cx - 8, cy - 4), (cx - 4, cy),
                                             (cx, cy - 7), (cx + 4, cy), (cx + 8, cy - 4), (cx + 8, cy + 6)])
            sc = self.font_small.render(str(r["score"]), True, color)
            s.blit(sc, sc.get_rect(topright=(panel.x + 240, y + 2)))
            ch = self.font_small.render(str(r.get("chests", 0)), True, INK_SOFT)
            s.blit(ch, ch.get_rect(topright=(panel.x + 292, y + 2)))
            cb = self.font_small.render(str(r.get("combo", 0)), True, INK_SOFT)
            s.blit(cb, cb.get_rect(topright=(panel.x + 344, y + 2)))
            y += 31

    def draw(self):
        if self.state == TITLE:
            self.draw_title()
        elif self.state == INTRO:
            self.draw_intro()
        elif self.state == PLAYING:
            self.draw_playing()
        elif self.state == PAUSED:
            self.draw_paused()
        elif self.state == LEVEL_COMPLETE:
            self.draw_level_complete()
        elif self.state == WIN:
            self.draw_end_screen(won=True)
        elif self.state == GAME_OVER:
            self.draw_end_screen(won=False)
        self.fade.draw(self.surface)
        self.present()

    def present(self):
        ox, oy, w, h = self.viewport()
        sx, sy = self.shake.offset()
        if (ox, oy) != (0, 0) or sx or sy:
            self.window.fill(LETTERBOX)
        scale = w / LOGICAL_W
        # smoothscale costs tens of milliseconds per frame in WebAssembly,
        # which starves input; plain scale is nearest-neighbour but cheap.
        resize = pygame.transform.scale if data.IS_WEB else pygame.transform.smoothscale
        frame = self.surface if (w, h) == (LOGICAL_W, LOGICAL_H) else resize(self.surface, (w, h))
        self.window.blit(frame, (ox + int(sx * scale), oy + int(sy * scale)))
        pygame.display.flip()

    # ----------------------------------------------------------------- run
    async def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            self.handle_events()
            if not self.running:
                break
            self.update(dt)
            self.draw()
            # Hands the frame back to the browser's event loop; a no-op on desktop.
            await asyncio.sleep(0)
        pygame.quit()
