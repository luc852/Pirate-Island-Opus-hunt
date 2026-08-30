import asyncio
import math
import pygame

import data
import levels
import ui
from sprites import (
    TILE_SIZE, Wall, Coin, Puddle, Player, Monster, MONSTER_COLORS,
    draw_sand_background, draw_heart, load_coin_frames,
    draw_shoreline, draw_pirate_avatar, vertical_gradient,
)

LOGICAL_W, LOGICAL_H = 900, 600
HUD_H = 60
FPS = 60

TITLE = "title"
PLAYING = "playing"
LEVEL_COMPLETE = "level_complete"
GAME_OVER = "game_over"
WIN = "win"
LEADERBOARD = "leaderboard"

BG_SEA = (61, 155, 196)
PANEL = (255, 250, 235)
INK = (50, 40, 30)
GOLD = (222, 168, 46)

# Two extra ink steps end the all-INK flatness, and GOLD gains a lit and a
# shadow step so coins and chips can be dimensional.
INK_SOFT = (107, 90, 72)
INK_LABEL = (138, 106, 68)
GOLD_LIT = (247, 206, 71)
GOLD_DEEP = (169, 114, 15)
SEA_STOPS = [(0.0, (79, 168, 206)), (0.42, (61, 155, 196)), (1.0, (27, 99, 137))]
HUD_TOP = (233, 210, 156)
HUD_BOTTOM = (216, 186, 128)
HUD_EDGE = (138, 106, 68)


class Button:
    def __init__(self, rect, text, color=(240, 200, 90)):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.enabled = True

    def draw(self, surface, font, mouse=(-1, -1)):
        if not self.enabled:
            pygame.draw.rect(surface, (206, 196, 176), self.rect, border_radius=16)
            pygame.draw.rect(surface, (160, 148, 128), self.rect, 3, border_radius=16)
            label = font.render(self.text, True, (135, 124, 106))
            surface.blit(label, label.get_rect(center=self.rect.center))
            return
        hovered = self.rect.collidepoint(mouse)
        col = tuple(min(255, c + 20) for c in self.color) if hovered else self.color
        pygame.draw.rect(surface, (90, 60, 30), self.rect.move(0, 3), border_radius=16)
        pygame.draw.rect(surface, col, self.rect, border_radius=16)
        pygame.draw.rect(surface, (90, 60, 30), self.rect, 3, border_radius=16)
        label = font.render(self.text, True, INK)
        surface.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, pos):
        return self.enabled and self.rect.collidepoint(pos)


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Pirate Island Coin Hunt")
        self.window = pygame.display.set_mode((LOGICAL_W, LOGICAL_H), pygame.RESIZABLE)
        self.surface = pygame.Surface((LOGICAL_W, LOGICAL_H))
        self.clock = pygame.time.Clock()

        self.font_small = pygame.font.SysFont("arial", 20)
        self.font_med = pygame.font.SysFont("arial", 28, bold=True)
        self.font_big = pygame.font.SysFont("arial", 52, bold=True)
        self.font_hud = pygame.font.SysFont("arial", 22, bold=True)
        self.font_label = pygame.font.SysFont("arial", 11, bold=True)

        # Backdrops that never change: built once rather than per frame.
        self.sea = vertical_gradient(LOGICAL_W, LOGICAL_H, SEA_STOPS)
        self.hud_band = vertical_gradient(LOGICAL_W, HUD_H,
                                          [(0.0, HUD_TOP), (1.0, HUD_BOTTOM)])

        self.coin_frames = load_coin_frames()
        self.coin_icon = pygame.transform.smoothscale(self.coin_frames[0], (24, 24))
        self.scores = data.load_scores()

        self.running = True
        self.last_resize = None
        self.state = TITLE
        self.mouse = (0, 0)
        self.player_name = None
        self.save_score = True
        self.previous_best = 0
        self.level_index = 0
        self.lives = 3
        self.score = 0
        self.total_coins_collected = 0

        # Title screen: pick a registered pirate, or type a fresh name.
        self.combo = ui.ComboBox((125, 226, 300, 46))
        self.name_field = ui.TextField((475, 226, 300, 46), max_len=data.MAX_NAME_LEN)
        self.save_checkbox = ui.Checkbox((475, 292), "Save my name and score", checked=True)
        self.play_button = Button((350, 492, 200, 56), "Set Sail!")
        self.refresh_roster()

        self.continue_button = Button((350, 480, 200, 55), "Continue")
        self.retry_button = Button((350, 480, 200, 55), "Play Again")

        self.message_timer = 0.0

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
        if self.name_field.key(event):
            if self.name_field.text:
                self.combo.selected = None
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.begin_from_title()
        elif event.key == pygame.K_ESCAPE:
            self.combo.open = False
            self.name_field.focused = False

    # ---------------------------------------------------------- level setup
    def load_level(self, index):
        cfg = levels.LEVELS[index]
        grid = cfg["grid"]
        rows = len(grid)
        cols = len(grid[0])

        self.grid_px_w = cols * TILE_SIZE
        self.grid_px_h = rows * TILE_SIZE
        self.ox = (LOGICAL_W - self.grid_px_w) // 2
        self.oy = HUD_H + (LOGICAL_H - HUD_H - self.grid_px_h) // 2

        self.bounds = pygame.Rect(0, 0, self.grid_px_w, self.grid_px_h)

        self.walls = []
        self.coins = []
        self.puddles = []
        self.monsters = []
        player_start = (1, 1)

        color = MONSTER_COLORS[index % len(MONSTER_COLORS)]
        for r, row in enumerate(grid):
            for c, ch in enumerate(row):
                if ch == '#':
                    self.walls.append(Wall(c, r))
                elif ch == 'C':
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

    def start_new_game(self, player_name, save_score=True):
        self.player_name = player_name
        self.save_score = save_score
        if save_score:
            data.register_player(self.scores, player_name)
            self.refresh_roster()
        self.level_index = 0
        self.lives = 3
        self.score = 0
        self.total_coins_collected = 0
        self.load_level(0)
        self.state = PLAYING

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
            elif event.type == pygame.KEYDOWN and self.state == TITLE:
                self.handle_title_key(event)

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
        elif self.state == LEVEL_COMPLETE:
            if self.continue_button.clicked(pos):
                self.level_index += 1
                if self.level_index >= len(levels.LEVELS):
                    self.finish_game(won=True)
                else:
                    self.load_level(self.level_index)
                    self.state = PLAYING
        elif self.state in (GAME_OVER, WIN, LEADERBOARD):
            if self.retry_button.clicked(pos):
                self.name_field.text = ""
                self.name_field.focused = False
                self.combo.open = False
                self.combo.selected = self.player_name if self.save_score else None
                self.state = TITLE

    def finish_game(self, won):
        self.previous_best = data.best_score(self.scores, self.player_name)
        if self.save_score:
            self.scores = data.record_score(self.scores, self.player_name, self.score)
            self.refresh_roster()
        self.state = WIN if won else GAME_OVER

    def get_keys(self):
        pressed = pygame.key.get_pressed()
        return {
            "left": pressed[pygame.K_LEFT] or pressed[pygame.K_a],
            "right": pressed[pygame.K_RIGHT] or pressed[pygame.K_d],
            "up": pressed[pygame.K_UP] or pressed[pygame.K_w],
            "down": pressed[pygame.K_DOWN] or pressed[pygame.K_s],
        }

    def update_playing(self, dt):
        keys = self.get_keys()
        self.player.update(dt, keys, self.wall_rects, self.bounds)

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
                    self.score += 10

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
            if hit:
                self.lives -= 1
                self.player.start_invincibility()
                if self.lives <= 0:
                    self.finish_game(won=False)
                    return

        if self.coins_collected_level >= self.total_coins and self.total_coins > 0:
            self.score += 50
            self.state = LEVEL_COMPLETE

    def update(self, dt):
        self.mouse = self.to_logical_pos(pygame.mouse.get_pos())
        if self.state == PLAYING:
            self.update_playing(dt)
        elif self.state == TITLE:
            self.name_field.update(dt)

    # ---------------------------------------------------------------- draw
    def draw_hud(self):
        """Four labelled zones laid out left to right, rather than text dropped
        at hard-coded x offsets of 20 / 260 / 410."""
        mid = HUD_H // 2
        self.surface.blit(self.hud_band, (0, 0))
        pygame.draw.line(self.surface, HUD_EDGE, (0, HUD_H - 2), (LOGICAL_W, HUD_H - 2), 3)

        x = 18

        # Level chip
        cap = self.font_label.render("LEVEL", True, (199, 169, 112))
        num = self.font_hud.render(f"{self.level_index + 1}", True, PANEL)
        den = self.font_small.render(f"/{len(levels.LEVELS)}", True, (156, 133, 98))
        pill_w = 14 + cap.get_width() + 8 + num.get_width() + den.get_width() + 14
        pill = pygame.Rect(x, mid - 17, pill_w, 34)
        pygame.draw.rect(self.surface, INK, pill, border_radius=17)
        self.surface.blit(cap, cap.get_rect(midleft=(pill.x + 14, mid)))
        self.surface.blit(num, num.get_rect(midleft=(pill.x + 14 + cap.get_width() + 8, mid)))
        self.surface.blit(den, den.get_rect(bottomleft=(
            pill.x + 14 + cap.get_width() + 8 + num.get_width(), mid + 10)))
        x = pill.right + 20

        # Lives
        for i in range(3):
            draw_heart(self.surface, x + 13 + i * 31, mid, 26, filled=i < self.lives)
        x += 3 * 31 + 8

        # Coins: the count plus how much of the island is left
        self.surface.blit(self.coin_icon, self.coin_icon.get_rect(center=(x + 12, mid)))
        x += 33
        found = self.font_hud.render(f"{self.coins_collected_level}", True, INK)
        total = self.font_small.render(f"/{self.total_coins}", True, INK_LABEL)
        self.surface.blit(found, (x, mid - 18))
        self.surface.blit(total, (x + found.get_width(), mid - 12))
        track = pygame.Rect(x, mid + 8, 96, 6)
        pygame.draw.rect(self.surface, (168, 140, 100), track, border_radius=3)
        if self.total_coins:
            filled = int(track.width * self.coins_collected_level / self.total_coins)
            if filled > 0:
                pygame.draw.rect(self.surface, GOLD_LIT,
                                 (track.x, track.y, filled, track.height), border_radius=3)

        # Right edge: crew, then score. Laid out from the right inward.
        rx = LOGICAL_W - 18
        name = self.font_small.render(self.player_name or "", True, INK)
        rx -= name.get_width()
        self.surface.blit(name, name.get_rect(midleft=(rx, mid)))
        rx -= 10 + 30
        draw_pirate_avatar(self.surface, rx + 15, mid, 15,
                           tint=(246, 238, 218))
        rx -= 18
        pygame.draw.line(self.surface, (168, 140, 100), (rx, mid - 14), (rx, mid + 14), 2)
        rx -= 18

        score_cap = self.font_label.render("SCORE", True, INK_LABEL)
        score_val = self.font_hud.render(str(self.score), True, INK)
        self.surface.blit(score_cap, score_cap.get_rect(topright=(rx, mid - 18)))
        self.surface.blit(score_val, score_val.get_rect(topright=(rx, mid - 4)))

    def draw_playing(self):
        self.surface.blit(self.sea, (0, 0))
        draw_shoreline(self.surface,
                       pygame.Rect(self.ox, self.oy, self.grid_px_w, self.grid_px_h))
        self.surface.blit(self.background, (self.ox, self.oy))
        for wall in self.walls:
            wall.draw(self.surface, self.ox, self.oy)
        for puddle in self.puddles:
            puddle.draw(self.surface, self.ox, self.oy)
        for coin in self.coins:
            coin.draw(self.surface, self.ox, self.oy)
        for monster in self.monsters:
            monster.draw(self.surface, self.ox, self.oy)
        self.player.draw(self.surface, self.ox, self.oy)
        self.draw_hud()

    def draw_title(self):
        self.surface.blit(self.sea, (0, 0))
        for i in range(6):
            pygame.draw.circle(self.surface, (108, 186, 218),
                               (60 + i * 160, 60 + (i % 2) * 40), 26, 2)

        title = self.font_big.render("Pirate Island Coin Hunt", True, (255, 250, 230))
        shadow = self.font_big.render("Pirate Island Coin Hunt", True, (60, 40, 20))
        self.surface.blit(shadow, shadow.get_rect(center=(LOGICAL_W // 2 + 3, 61)))
        self.surface.blit(title, title.get_rect(center=(LOGICAL_W // 2, 58)))

        self.draw_best_banner(118)

        panel = pygame.Rect(100, 160, 700, 300)
        pygame.draw.rect(self.surface, PANEL, panel, border_radius=20)
        pygame.draw.rect(self.surface, (90, 60, 30), panel, 3, border_radius=20)

        # Two ways aboard, side by side, split by an OR rule.
        head_left = self.font_med.render("Returning pirate", True, INK)
        self.surface.blit(head_left, head_left.get_rect(midleft=(125, 192)))
        head_right = self.font_med.render("New pirate", True, INK)
        self.surface.blit(head_right, head_right.get_rect(midleft=(475, 192)))

        pygame.draw.line(self.surface, (223, 210, 184), (450, 185), (450, 435), 2)
        or_chip = pygame.Rect(0, 0, 40, 28)
        or_chip.center = (450, 300)
        pygame.draw.rect(self.surface, PANEL, or_chip)
        or_label = self.font_small.render("or", True, INK_LABEL)
        self.surface.blit(or_label, or_label.get_rect(center=or_chip.center))

        typing = self.typing_new_name()
        self.combo.draw(self.surface, self.font_med, self.font_small, active=not typing)
        self.name_field.draw(self.surface, self.font_med, active=True)
        self.save_checkbox.draw(self.surface, self.font_small, active=typing)

        # Under each column, say what will actually happen.
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
            self.surface.blit(note, note.get_rect(midleft=(475, 336)))
        else:
            note = self.font_small.render(
                f"{len(self.combo.items)} pirate(s) registered", True, INK_LABEL)
            self.surface.blit(note, note.get_rect(midleft=(125, 292)))

        self.play_button.enabled = bool(self.chosen_name())
        self.play_button.draw(self.surface, self.font_med, self.mouse)

        hint = self.font_small.render(
            "Arrows or WASD to move - Enter to set sail", True, (226, 240, 248))
        self.surface.blit(hint, hint.get_rect(center=(LOGICAL_W // 2, 575)))

        # Last, so the open list floats over the panel and the button.
        self.combo.draw_list(self.surface, self.font_small, self.mouse)


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

    def draw_level_complete(self):
        self.draw_playing()
        overlay = pygame.Surface((LOGICAL_W, LOGICAL_H), pygame.SRCALPHA)
        overlay.fill((20, 20, 20, 140))
        self.surface.blit(overlay, (0, 0))

        panel = pygame.Rect(LOGICAL_W // 2 - 260, 170, 520, 300)
        pygame.draw.rect(self.surface, PANEL, panel, border_radius=22)
        pygame.draw.rect(self.surface, GOLD, panel, 4, border_radius=22)

        title = self.font_big.render("Level Complete!", True, (60, 150, 70))
        self.surface.blit(title, title.get_rect(center=(LOGICAL_W // 2, 230)))
        msg = self.font_med.render(f"Score: {self.score}", True, INK)
        self.surface.blit(msg, msg.get_rect(center=(LOGICAL_W // 2, 290)))
        for i in range(5):
            draw_heart(self.surface, LOGICAL_W // 2 - 60 + i * 30, 340, 20, filled=True)
        self.continue_button.draw(self.surface, self.font_med, self.mouse)

    def draw_end_screen(self, won):
        self.surface.fill((72, 130, 170) if won else (90, 90, 100))
        panel = pygame.Rect(LOGICAL_W // 2 - 280, 60, 560, 265)
        pygame.draw.rect(self.surface, PANEL, panel, border_radius=22)
        pygame.draw.rect(self.surface, GOLD if won else (150, 150, 150), panel, 4, border_radius=22)

        if won:
            title = self.font_big.render("You win, matey!", True, (60, 150, 70))
            sub_text = "You collected all the treasure on every island!"
        else:
            title = self.font_big.render("Game Over", True, (170, 70, 70))
            sub_text = "Better luck next time, sailor. Take a breath and try again!"

        self.surface.blit(title, title.get_rect(center=(LOGICAL_W // 2, 112)))
        sub = self.font_small.render(sub_text, True, INK)
        self.surface.blit(sub, sub.get_rect(center=(LOGICAL_W // 2, 158)))
        score_label = self.font_med.render(
            f"{self.player_name} - Final Score: {self.score}", True, INK)
        self.surface.blit(score_label, score_label.get_rect(center=(LOGICAL_W // 2, 205)))

        if self.save_score:
            best = data.best_score(self.scores, self.player_name)
            note = f"Your best: {best}"
            if self.score > self.previous_best:
                note += "  -  new personal record!"
            color = INK
        else:
            note = "Guest run - this score was not saved"
            color = (150, 90, 60)
        best_label = self.font_small.render(note, True, color)
        self.surface.blit(best_label, best_label.get_rect(center=(LOGICAL_W // 2, 255)))

        self.draw_leaderboard_panel(345)
        self.retry_button.rect.topleft = (LOGICAL_W // 2 - 100, 528)
        self.retry_button.text = "Back to Title"
        self.retry_button.draw(self.surface, self.font_med, self.mouse)

    def draw_leaderboard_panel(self, top_y, rows=5):
        """Top few pirates, plus the current one pinned on if they ranked lower."""
        ranking = data.ranking(self.scores)
        shown = ranking[:rows]
        if self.save_score and self.player_name and \
                self.player_name not in [n for n, _ in shown]:
            place = next((i for i, (n, _) in enumerate(ranking)
                          if n == self.player_name), None)
            if place is not None:
                shown = shown[:rows - 1] + [ranking[place]]

        panel = pygame.Rect(LOGICAL_W // 2 - 280, top_y, 560, 30 + max(1, len(shown)) * 23 + 8)
        pygame.draw.rect(self.surface, (255, 255, 255), panel, border_radius=14)
        pygame.draw.rect(self.surface, (90, 60, 30), panel, 2, border_radius=14)
        header = self.font_small.render("Leaderboard (best scores)", True, INK)
        self.surface.blit(header, (panel.x + 16, panel.y + 6))

        if not shown:
            empty = self.font_small.render("No saved scores yet.", True, INK_LABEL)
            self.surface.blit(empty, (panel.x + 16, panel.y + 32))
            return

        for i, (name, best) in enumerate(shown):
            place = next(j for j, (n, _) in enumerate(ranking) if n == name)
            highlight = self.save_score and name == self.player_name
            color = (200, 40, 40) if highlight else INK
            y = panel.y + 32 + i * 23
            marker = ">" if highlight else " "
            label = self.font_small.render(f"{marker} {place + 1}. {name}", True, color)
            self.surface.blit(label, (panel.x + 16, y))
            value = self.font_small.render(str(best), True, color)
            self.surface.blit(value, value.get_rect(topright=(panel.right - 16, y)))

    def draw(self):
        if self.state == TITLE:
            self.draw_title()
        elif self.state == PLAYING:
            self.draw_playing()
        elif self.state == LEVEL_COMPLETE:
            self.draw_level_complete()
        elif self.state == WIN:
            self.draw_end_screen(won=True)
        elif self.state == GAME_OVER:
            self.draw_end_screen(won=False)

        ox, oy, w, h = self.viewport()
        if (ox, oy) != (0, 0):
            self.window.fill(SEA_STOPS[-1][1])
        # smoothscale costs tens of milliseconds per frame in WebAssembly,
        # which starves input; plain scale is nearest-neighbour but cheap.
        resize = pygame.transform.scale if data.IS_WEB else pygame.transform.smoothscale
        self.window.blit(resize(self.surface, (w, h)), (ox, oy))
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
