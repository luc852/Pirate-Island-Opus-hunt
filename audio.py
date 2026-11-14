"""Sound, synthesized at start-up so the game ships no audio files.

Every effect is built from sine/square waves and filtered noise into 16-bit
PCM and handed to pygame.mixer as a raw buffer. Nothing here may crash the
game: if the mixer cannot start (no audio device, a browser that refuses), the
whole module degrades to silence.
"""
import math
import random
from array import array

import pygame

_rate = 22050
_channels = 1
_ok = False
_muted = False
_sounds = {}
_ambient_channel = None
_storm_channel = None


def _to_sound(samples):
    """Float samples in -1..1 -> pygame Sound in the mixer's own format."""
    buf = array("h")
    if _channels == 1:
        buf.extend(int(max(-1.0, min(1.0, s)) * 30000) for s in samples)
    else:
        for s in samples:
            v = int(max(-1.0, min(1.0, s)) * 30000)
            for _ in range(_channels):
                buf.append(v)
    return pygame.mixer.Sound(buffer=buf.tobytes())


def _env(i, n, attack=0.01, release=0.9):
    """Linear attack, exponential-ish decay. i/n is position in the sound."""
    t = i / n
    if t < attack:
        return t / attack
    return (1.0 - t) ** (1.0 + release * 2)


def _tone(freqs, dur, wave="sine", vol=0.5, attack=0.01, release=0.9, slide=0.0):
    """A note (or chord if `freqs` is a list) with an optional pitch slide."""
    if not isinstance(freqs, (list, tuple)):
        freqs = [freqs]
    n = int(_rate * dur)
    out = [0.0] * n
    for f in freqs:
        phase = 0.0
        for i in range(n):
            fi = f * (1.0 + slide * i / n)
            phase += fi / _rate
            p = phase % 1.0
            if wave == "square":
                v = 1.0 if p < 0.5 else -1.0
            elif wave == "saw":
                v = 2.0 * p - 1.0
            elif wave == "tri":
                v = 4.0 * abs(p - 0.5) - 1.0
            else:
                v = math.sin(2 * math.pi * p)
            out[i] += v * vol / len(freqs) * _env(i, n, attack, release)
    return out


def _noise(dur, vol=0.5, smooth=0.0, attack=0.005, release=0.9, seed=1):
    """Noise through a one-pole low-pass: smooth 0 = hiss, 0.98 = rumble."""
    rnd = random.Random(seed)
    n = int(_rate * dur)
    out = []
    last = 0.0
    gain = 1.0 / max(0.05, 1.0 - smooth) ** 0.5
    for i in range(n):
        last = last * smooth + rnd.uniform(-1, 1) * (1 - smooth)
        out.append(last * gain * vol * _env(i, n, attack, release))
    return out


def _seq(notes, wave="square", vol=0.25, gap=0.0):
    """A little melody: [(freq or 0 for rest, seconds), ...]."""
    out = []
    for f, d in notes:
        if f:
            out.extend(_tone(f, d, wave, vol, attack=0.02, release=0.5))
        else:
            out.extend([0.0] * int(_rate * d))
        out.extend([0.0] * int(_rate * gap))
    return out


def _mix(*parts):
    n = max(len(p) for p in parts)
    out = [0.0] * n
    for p in parts:
        for i, v in enumerate(p):
            out[i] += v
    return out


def _surf_loop(dur=4.0):
    """Breaking surf: brown noise swelling twice per loop, so it loops clean."""
    rnd = random.Random(7)
    n = int(_rate * dur)
    out = []
    last = 0.0
    for i in range(n):
        last = last * 0.985 + rnd.uniform(-1, 1) * 0.015
        swell = 0.55 + 0.45 * math.sin(2 * math.pi * 2 * i / n) ** 2
        out.append(last * 6.0 * swell * 0.5)
    # Cross-fade the seam.
    fade = int(_rate * 0.2)
    for i in range(fade):
        k = i / fade
        out[i] = out[i] * k + out[n - fade + i] * (1 - k)
    return out[: n - fade]


def _rain_loop(dur=2.0):
    rnd = random.Random(3)
    n = int(_rate * dur)
    out = []
    last = 0.0
    for i in range(n):
        last = last * 0.6 + rnd.uniform(-1, 1) * 0.4
        out.append(last * 0.22)
    return out


C4, D4, E4, F4, G4, A4, B4 = 262, 294, 330, 349, 392, 440, 494
C5, D5, E5, G5, A5 = 523, 587, 659, 784, 880


def _build():
    s = {}
    s["coin"] = _mix(_tone(988, 0.07, "square", 0.18), [0.0] * int(_rate * 0.05)
                     + _tone(1319, 0.16, "square", 0.18))
    # Combo coins climb in pitch so a streak is audible.
    for step in range(1, 4):
        k = 2 ** (step * 2 / 12)
        s[f"coin{step}"] = _mix(_tone(988 * k, 0.06, "square", 0.18),
                                [0.0] * int(_rate * 0.04) + _tone(1319 * k, 0.16, "square", 0.18))
    s["hit"] = _mix(_noise(0.25, 0.6, smooth=0.9), _tone(180, 0.3, "saw", 0.35, slide=-0.6))
    s["dig"] = _mix(_noise(0.12, 0.35, smooth=0.5),
                    [0.0] * int(_rate * 0.15) + _noise(0.12, 0.35, smooth=0.5, seed=4))
    s["miss"] = _tone(220, 0.25, "tri", 0.3, slide=-0.3)
    s["chest"] = _seq([(C5, 0.08), (E5, 0.08), (G5, 0.08), (C5 * 2, 0.32)], "square", 0.2)
    s["thunder"] = _noise(2.2, 0.9, smooth=0.97, attack=0.02, release=0.5, seed=9)
    s["kraken"] = _mix(_tone(55, 1.1, "saw", 0.45, attack=0.2, slide=0.3),
                       _tone(82, 1.1, "saw", 0.25, attack=0.3, slide=-0.2),
                       _noise(1.1, 0.25, smooth=0.95, attack=0.3))
    s["slam"] = _mix(_noise(0.35, 0.7, smooth=0.93), _tone(70, 0.35, "sine", 0.5, slide=-0.5))
    s["cannon"] = _mix(_noise(0.6, 0.9, smooth=0.95), _tone(60, 0.5, "sine", 0.6, slide=-0.6))
    s["whistle"] = _tone(1400, 0.5, "sine", 0.12, attack=0.1, slide=-0.55)
    s["event"] = _seq([(A4, 0.12), (0, 0.04), (A4, 0.12), (F4, 0.35)], "saw", 0.16)
    s["clear"] = _seq([(G4, 0.12), (C5, 0.12), (E5, 0.12), (G5, 0.3)], "square", 0.18)
    s["start"] = _seq([(D4, 0.14), (G4, 0.14), (G4, 0.07), (A4, 0.07), (B4, 0.14),
                       (G4, 0.14), (B4, 0.14), (A4, 0.28)], "square", 0.13)
    s["win"] = _seq([(G4, 0.15), (C5, 0.15), (E5, 0.15), (G5, 0.15), (E5, 0.12),
                     (G5, 0.5)], "square", 0.17)
    s["lose"] = _seq([(G4, 0.22), (F4, 0.22), (E4, 0.22), (D4, 0.22), (C4, 0.6)], "tri", 0.25)
    s["legend"] = _seq([(C5, 0.15), (G4, 0.15), (C5, 0.15), (E5, 0.15), (G5, 0.15),
                        (C5 * 2, 0.15), (G5, 0.15), (C5 * 2, 0.7)], "square", 0.18)
    s["tick"] = _tone(1760, 0.03, "square", 0.08)
    s["piece"] = _seq([(E5, 0.1), (G5, 0.1), (A5, 0.25)], "tri", 0.3)
    s["click"] = _tone(660, 0.04, "tri", 0.2)
    s["surf"] = _surf_loop()
    s["rain"] = _rain_loop()
    return s


def init():
    """Start the mixer and synthesize every sound. Safe to call once."""
    global _ok, _rate, _channels, _sounds
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(22050, -16, 1, 512)
        freq, size, channels = pygame.mixer.get_init()
        if abs(size) != 16:
            return False
        # Synthesis cost scales with the rate; the browser often insists on
        # 44.1/48 kHz, so generate at that rate rather than resample.
        _rate, _channels = freq, channels
        raw = _build()
        _sounds = {k: _to_sound(v) for k, v in raw.items()}
        pygame.mixer.set_num_channels(16)
        _ok = True
    except Exception:
        _ok = False
    return _ok


def play(name, volume=1.0):
    if not _ok or _muted:
        return
    snd = _sounds.get(name)
    if snd is None:
        return
    try:
        ch = snd.play()
        if ch is not None:
            ch.set_volume(volume)
    except Exception:
        pass


def start_ambient():
    global _ambient_channel
    if not _ok:
        return
    try:
        if _ambient_channel is None or not _ambient_channel.get_busy():
            _ambient_channel = _sounds["surf"].play(loops=-1)
        if _ambient_channel is not None:
            _ambient_channel.set_volume(0.0 if _muted else 0.35)
    except Exception:
        pass


def set_storm(on):
    global _storm_channel
    if not _ok:
        return
    try:
        if on and (_storm_channel is None or not _storm_channel.get_busy()):
            _storm_channel = _sounds["rain"].play(loops=-1, fade_ms=800)
            if _storm_channel is not None:
                _storm_channel.set_volume(0.0 if _muted else 0.5)
        elif not on and _storm_channel is not None:
            _storm_channel.fadeout(900)
            _storm_channel = None
    except Exception:
        pass


def toggle_mute():
    global _muted
    _muted = not _muted
    if _ok:
        try:
            if _muted:
                pygame.mixer.stop()
            global _ambient_channel, _storm_channel
            _ambient_channel = None
            _storm_channel = None
            start_ambient()
        except Exception:
            pass
    return _muted


def is_muted():
    return _muted


def available():
    return _ok
