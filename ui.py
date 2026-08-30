"""Small pygame widgets used by the title screen: combo box, text field, checkbox.

They share the parchment-and-ink look of the rest of the game and only need to
be told about clicks, key presses and wheel scrolls.
"""
import pygame

INK = (50, 40, 30)
INK_SOFT = (107, 90, 72)
INK_LABEL = (138, 106, 68)
PANEL = (255, 250, 235)
FIELD = (247, 238, 216)
FIELD_EDGE = (168, 140, 100)
GOLD = (222, 168, 46)
GOLD_DEEP = (169, 114, 15)
ROW_HOVER = (243, 226, 184)
DISABLED = (238, 230, 212)


def shadowed_box(surface, rect, fill, radius=12, edge=INK, width=2, lift=3):
    pygame.draw.rect(surface, (150, 122, 84), rect.move(0, lift), border_radius=radius)
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, edge, rect, width, border_radius=radius)


class ComboBox:
    """A closed pill that drops a scrollable list of (name, score) rows."""

    ROW_H = 32
    MAX_VISIBLE = 5

    def __init__(self, rect, placeholder="Choose a pirate"):
        self.rect = pygame.Rect(rect)
        self.placeholder = placeholder
        self.items = []
        self.selected = None
        self.open = False
        self.scroll = 0

    def set_items(self, items):
        self.items = list(items)
        if self.selected is not None and self.selected not in [n for n, _ in self.items]:
            self.selected = None
        self.scroll = max(0, min(self.scroll, self.max_scroll()))

    def max_scroll(self):
        return max(0, len(self.items) - self.MAX_VISIBLE)

    @property
    def visible_rows(self):
        return min(len(self.items), self.MAX_VISIBLE)

    def list_rect(self):
        h = self.visible_rows * self.ROW_H + 8
        return pygame.Rect(self.rect.x, self.rect.bottom + 6, self.rect.width, h)

    def row_rect(self, i):
        top = self.list_rect().y + 4 + i * self.ROW_H
        return pygame.Rect(self.rect.x + 4, top, self.rect.width - 8, self.ROW_H)

    def score_of(self, name):
        for n, s in self.items:
            if n == name:
                return s
        return 0

    # ------------------------------------------------------------- events
    def click(self, pos):
        """Returns "opened", "closed", "selected", or None if the click missed."""
        if self.rect.collidepoint(pos):
            if not self.items:
                return None
            self.open = not self.open
            return "opened" if self.open else "closed"
        if self.open:
            if self.list_rect().collidepoint(pos):
                for i in range(self.visible_rows):
                    if self.row_rect(i).collidepoint(pos):
                        self.selected = self.items[i + self.scroll][0]
                        self.open = False
                        return "selected"
                return "closed"
            # A click outside just dismisses the list; it must not also press
            # whatever widget sits underneath.
            self.open = False
            return "closed"
        return None

    def wheel(self, pos, dy):
        if self.open and (self.list_rect().collidepoint(pos) or self.rect.collidepoint(pos)):
            self.scroll = max(0, min(self.max_scroll(), self.scroll - dy))
            return True
        return False

    # --------------------------------------------------------------- draw
    def draw(self, surface, font, font_small, active=True):
        edge = GOLD if (active and self.selected) else FIELD_EDGE
        shadowed_box(surface, self.rect, FIELD if active else DISABLED,
                     radius=14, edge=edge, width=3)

        if self.selected:
            text, color = self.selected, INK
        elif self.items:
            text, color = self.placeholder, INK_SOFT
        else:
            text, color = "No pirates yet", INK_SOFT
        label = font.render(text, True, color if active else INK_LABEL)
        surface.blit(label, label.get_rect(midleft=(self.rect.x + 16, self.rect.centery)))

        if self.selected:
            score = font_small.render("best " + str(self.score_of(self.selected)),
                                      True, INK_LABEL)
            surface.blit(score, score.get_rect(midright=(self.rect.right - 34,
                                                         self.rect.centery + 1)))
        cx, cy = self.rect.right - 20, self.rect.centery
        if self.open:
            pts = [(cx - 7, cy + 3), (cx + 7, cy + 3), (cx, cy - 5)]
        else:
            pts = [(cx - 7, cy - 3), (cx + 7, cy - 3), (cx, cy + 5)]
        pygame.draw.polygon(surface, INK_SOFT, pts)

    def draw_list(self, surface, font_small, mouse=(-1, -1)):
        """Drawn separately so the open list floats above every other widget."""
        if not self.open or not self.items:
            return
        box = self.list_rect()
        shadowed_box(surface, box, PANEL, radius=12, edge=FIELD_EDGE, width=2)
        for i in range(self.visible_rows):
            name, score = self.items[i + self.scroll]
            row = self.row_rect(i)
            if row.collidepoint(mouse):
                pygame.draw.rect(surface, ROW_HOVER, row, border_radius=8)
            rank = font_small.render(str(i + self.scroll + 1) + ".", True, INK_LABEL)
            surface.blit(rank, rank.get_rect(midleft=(row.x + 10, row.centery)))
            label = font_small.render(name, True, INK)
            surface.blit(label, label.get_rect(midleft=(row.x + 38, row.centery)))
            value = font_small.render(str(score), True, GOLD_DEEP if score else INK_LABEL)
            surface.blit(value, value.get_rect(midright=(row.right - 14, row.centery)))

        if self.max_scroll():
            track = pygame.Rect(box.right - 7, box.y + 6, 3, box.height - 12)
            pygame.draw.rect(surface, (223, 210, 184), track, border_radius=2)
            span = track.height * self.visible_rows / len(self.items)
            top = track.y + (track.height - span) * self.scroll / self.max_scroll()
            pygame.draw.rect(surface, FIELD_EDGE, (track.x, top, 3, span), border_radius=2)


class TextField:
    def __init__(self, rect, placeholder="Type a new name", max_len=14):
        self.rect = pygame.Rect(rect)
        self.placeholder = placeholder
        self.max_len = max_len
        self.text = ""
        self.focused = False
        self.caret_timer = 0.0

    def click(self, pos):
        self.focused = self.rect.collidepoint(pos)
        return self.focused

    def key(self, event):
        """Returns True when the field consumed the key press."""
        if not self.focused:
            return False
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
            return True
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB, pygame.K_ESCAPE):
            return False
        ch = event.unicode
        if ch and ch.isprintable() and len(self.text) < self.max_len:
            if ch != " " or self.text:   # no leading spaces
                self.text += ch
            return True
        return False

    def update(self, dt):
        self.caret_timer = (self.caret_timer + dt) % 1.0

    def draw(self, surface, font, active=True):
        edge = GOLD if (self.focused and active) else FIELD_EDGE
        shadowed_box(surface, self.rect, FIELD if active else DISABLED,
                     radius=14, edge=edge, width=3)
        shown = self.text or ("" if self.focused else self.placeholder)
        color = INK if self.text else INK_SOFT
        label = font.render(shown, True, color)
        x = self.rect.x + 16
        surface.blit(label, label.get_rect(midleft=(x, self.rect.centery)))
        if self.focused and self.caret_timer < 0.5:
            caret_x = x + label.get_width() + (2 if self.text else 0)
            pygame.draw.line(surface, INK, (caret_x, self.rect.centery - 12),
                             (caret_x, self.rect.centery + 12), 2)


class Checkbox:
    def __init__(self, pos, label, checked=True, box=24):
        self.rect = pygame.Rect(pos[0], pos[1], box, box)
        self.label = label
        self.checked = checked
        self.hit_width = box + 12

    def click(self, pos):
        area = pygame.Rect(self.rect.x, self.rect.y - 4,
                           self.hit_width, self.rect.height + 8)
        if area.collidepoint(pos):
            self.checked = not self.checked
            return True
        return False

    def draw(self, surface, font, active=True):
        pygame.draw.rect(surface, FIELD if active else DISABLED, self.rect, border_radius=6)
        pygame.draw.rect(surface, INK_SOFT if active else FIELD_EDGE,
                         self.rect, 2, border_radius=6)
        if self.checked:
            cx, cy = self.rect.center
            tick = [(cx - 6, cy), (cx - 2, cy + 5), (cx + 7, cy - 6)]
            pygame.draw.lines(surface, GOLD_DEEP if active else INK_LABEL, False, tick, 3)
        label = font.render(self.label, True, INK if active else INK_LABEL)
        surface.blit(label, label.get_rect(midleft=(self.rect.right + 10, self.rect.centery)))
        self.hit_width = self.rect.width + 10 + label.get_width()
