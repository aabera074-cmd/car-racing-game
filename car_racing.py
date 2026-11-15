import array
import math
import random

import pygame

# ---------------------------------------------------------------- setup
pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()
try:
    if not pygame.mixer.get_init():
        pygame.mixer.init(22050, -16, 1, 512)
except Exception:
    pass
SOUND_OK = pygame.mixer.get_init() is not None
if SOUND_OK:
    pygame.mixer.set_num_channels(12)
    pygame.mixer.set_reserved(1)  # channel 0 is the engine loop

info = pygame.display.Info()
W = info.current_w if info.current_w > 0 else 400
H = info.current_h if info.current_h > 0 else 700
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Car Racing")
WORLD = pygame.Surface((W, H))
clock = pygame.time.Clock()

# ---------------------------------------------------------------- colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
ROAD_GRAY = (45, 45, 48)
GRASS_DARK = (30, 125, 40)
GRASS_LIGHT = (38, 145, 48)
RED = (220, 40, 40)
BLUE = (30, 144, 255)
YELLOW = (255, 225, 50)
ORANGE = (255, 140, 0)
CYAN = (0, 235, 255)
PANEL = (10, 15, 40)  # dark HUD background: keeps text readable at any speed
DIFF_COLORS = {"Easy": (46, 160, 80), "Medium": (240, 150, 30), "Hard": (210, 50, 50)}
ENEMY_COLORS = [RED, (255, 215, 0), (0, 220, 120), (255, 105, 180), (160, 90, 255), (240, 240, 240)]

# ---------------------------------------------------------------- layout
HS = max(0.6, min(H / 700.0, 1.6))                 # speed scale
ROAD_W = min(int(W * 0.78), int(H * 0.55))
ROAD_X = (W - ROAD_W) // 2
LANE_W = ROAD_W / 3.0
CAR_S = LANE_W * 0.46 / 40.0
CAR_W = int(40 * CAR_S)
CAR_H = int(68 * CAR_S)
KERB_W = max(6, int(ROAD_W * 0.035))
U = min(W, H * 0.62)                               # UI unit


def mkfont(size):
    return pygame.font.SysFont("Arial", max(10, int(size)), bold=True)


font_s = mkfont(U * 0.04)
font_btn = mkfont(U * 0.048)
font = mkfont(U * 0.055)
font_l = mkfont(U * 0.09)
font_title = mkfont(U * 0.115)
font_xl = mkfont(U * 0.2)


def draw_text(surf, text, f, color, pos, anchor="center", outline=BLACK, ow=2):
    img = f.render(text, True, color)
    rect = img.get_rect(**{anchor: pos})
    if outline:
        o = f.render(text, True, outline)
        for dx in (-ow, 0, ow):
            for dy in (-ow, 0, ow):
                if dx or dy:
                    surf.blit(o, rect.move(dx, dy))
    surf.blit(img, rect)
    return rect


def outlined_surface(text, f, color, ow=3):
    img = f.render(text, True, color)
    o = f.render(text, True, BLACK)
    s = pygame.Surface((img.get_width() + ow * 2, img.get_height() + ow * 2), pygame.SRCALPHA)
    for dx in (0, ow, 2 * ow):
        for dy in (0, ow, 2 * ow):
            if dx != ow or dy != ow:
                s.blit(o, (dx, dy))
    s.blit(img, (ow, ow))
    return s


def blit_scaled_text(text, f, color, center, scale):
    s = outlined_surface(text, f, color)
    w = max(2, int(s.get_width() * scale))
    h = max(2, int(s.get_height() * scale))
    s = pygame.transform.smoothscale(s, (w, h))
    screen.blit(s, s.get_rect(center=center))


# ---------------------------------------------------------------- sound (generated in code)
SR = 22050
CH = pygame.mixer.get_init()[2] if SOUND_OK else 1


def make_sound(samples):
    if not SOUND_OK:
        return None
    a = array.array("h")
    for v in samples:
        v = max(-32767, min(32767, int(v)))
        a.append(v)
        if CH == 2:
            a.append(v)
    try:
        return pygame.mixer.Sound(buffer=a.tobytes())
    except Exception:
        return None


def tone(freq, dur, vol=0.5, fade=True, sweep=0.0):
    n = int(SR * dur)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / n
        ph += 2 * math.pi * (freq + sweep * t) / SR
        env = (1 - t) if fade else 1.0
        env *= min(1.0, i / 100.0)
        out.append(32767 * vol * env * math.sin(ph))
    return out


def noise(dur, vol=0.5, power=2.0, smooth=0.0):
    n = int(SR * dur)
    out = []
    y = 0.0
    for i in range(n):
        t = i / n
        x = random.uniform(-1, 1)
        if smooth > 0:
            y += smooth * (x - y)
            x = y * 3.0
        out.append(32767 * vol * x * ((1 - t) ** power))
    return out


def mix(*tracks):
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for t in tracks:
        for i, v in enumerate(t):
            out[i] += v
    return out


def concat(*tracks):
    out = []
    for t in tracks:
        out.extend(t)
    return out


def engine_loop(level):
    n = int(SR * 0.2)
    cycles = round((50 + level * 12) * 0.2)  # whole cycles -> seamless loop
    out = []
    for i in range(n):
        p = 2 * math.pi * cycles * i / n
        v = math.sin(p) + 0.5 * math.sin(2 * p) + 0.35 * math.sin(3 * p) + 0.2 * math.sin(5 * p)
        out.append(32767 * 0.2 * v)
    return out


MAX_LEVEL = 10
SOUNDS = {}
ENGINE_SOUNDS = []
if SOUND_OK:
    try:
        SOUNDS["click"] = make_sound(tone(900, 0.05, 0.4))
        SOUNDS["beep"] = make_sound(tone(660, 0.15, 0.5))
        SOUNDS["go"] = make_sound(tone(990, 0.35, 0.5))
        SOUNDS["levelup"] = make_sound(concat(tone(523, 0.1, 0.5), tone(659, 0.1, 0.5),
                                              tone(784, 0.1, 0.5), tone(1047, 0.25, 0.5)))
        SOUNDS["whoosh"] = make_sound(noise(0.25, 0.45, 1.5, 0.12))
        SOUNDS["crash"] = make_sound(mix(noise(0.9, 0.8, 2.0), tone(120, 0.9, 0.7, sweep=-90)))
        ENGINE_SOUNDS = [make_sound(engine_loop(l)) for l in range(1, MAX_LEVEL + 1)]
    except Exception:
        SOUNDS = {}
        ENGINE_SOUNDS = []

engine_ch = pygame.mixer.Channel(0) if SOUND_OK else None
engine_level = 0


def play(name):
    if sound_on and SOUNDS.get(name):
        SOUNDS[name].play()


def engine_set(lvl):
    global engine_level
    if not (SOUND_OK and sound_on and ENGINE_SOUNDS):
        return
    if engine_level != lvl or not engine_ch.get_busy():
        engine_ch.play(ENGINE_SOUNDS[lvl - 1], loops=-1)
        engine_ch.set_volume(0.5)
        engine_level = lvl


def engine_stop():
    global engine_level
    if SOUND_OK:
        engine_ch.stop()
    engine_level = 0


# ---------------------------------------------------------------- game data
DIFFS = {
    "Easy":   dict(base=4.2, inc=0.55, gap=520, gapmin=340, double=0.0),
    "Medium": dict(base=5.5, inc=0.85, gap=420, gapmin=260, double=0.12),
    "Hard":   dict(base=7.0, inc=1.15, gap=340, gapmin=210, double=0.3),
}
LEVEL_SCORE = 400
LANE_MULT = (0.85, 0.7, 0.55)  # enemy cars drive slower than you, lane by lane

difficulty = "Medium"
control_mode = "buttons"       # "buttons" or "wheel"
sound_on = True
cur_diff = dict(DIFFS[difficulty])

state = "menu"                 # menu, countdown, playing, settings, gameover
settings_return = "menu"
score = 0.0
high_score = 0
level = 1
speed = DIFFS[difficulty]["base"] * HS
scroll = 0.0
player_x = 0.0
vx = 0.0
tilt = 0.0
crash_tilt = 0.0
crash_pt = (0, 0)
enemies = []
spawn_dist = 0.0
next_gap = 300.0
cd_frames = 0
banner = 0
shake = 0
over_timer = 0
new_record = False
frame = 0
mouse_pressed = False
mpos = (0, 0)

wheel_angle = 0.0
wheel_drag = False
wheel_start_ptr = 0.0
wheel_start_ang = 0.0
WHEEL_MAX = 110.0

PARTS = []
POPS = []
TREES = []


def lane_x(l):
    return ROAD_X + LANE_W * (l + 0.5) - CAR_W / 2.0


# ---------------------------------------------------------------- drawing assets
CAR_CACHE = {}


def car_surface(color):
    if color in CAR_CACHE:
        return CAR_CACHE[color]
    s = pygame.Surface((40, 68), pygame.SRCALPHA)
    light = tuple(min(255, c + 50) for c in color)
    dark = tuple(max(0, c - 70) for c in color)
    for wx, wy in ((0, 12), (34, 12), (0, 46), (34, 46)):
        pygame.draw.rect(s, (15, 15, 15), (wx, wy, 6, 14), border_radius=2)
    pygame.draw.rect(s, color, (5, 4, 30, 60), border_radius=9)
    pygame.draw.rect(s, light, (8, 8, 3, 50), border_radius=2)
    pygame.draw.rect(s, (170, 215, 255), (10, 18, 20, 12), border_radius=3)
    pygame.draw.rect(s, dark, (10, 32, 20, 14), border_radius=3)
    pygame.draw.rect(s, (170, 215, 255), (10, 48, 20, 8), border_radius=3)
    pygame.draw.rect(s, dark, (8, 59, 24, 4), border_radius=2)
    pygame.draw.rect(s, YELLOW, (7, 2, 7, 4), border_radius=2)
    pygame.draw.rect(s, YELLOW, (26, 2, 7, 4), border_radius=2)
    pygame.draw.rect(s, (255, 40, 40), (7, 62, 7, 3), border_radius=1)
    pygame.draw.rect(s, (255, 40, 40), (26, 62, 7, 3), border_radius=1)
    s = pygame.transform.smoothscale(s, (CAR_W, CAR_H))
    CAR_CACHE[color] = s
    return s


def blit_car(surf, color, x, y, t=0.0):
    img = car_surface(color)
    if abs(t) > 0.5:
        img = pygame.transform.rotate(img, t)
    surf.blit(img, img.get_rect(center=(x + CAR_W / 2.0, y + CAR_H / 2.0)))


def build_wheel(r):
    s = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
    c = (r, r)
    pygame.draw.circle(s, (15, 15, 18), c, r)
    pygame.draw.circle(s, (75, 78, 92), c, int(r * 0.93))
    for a in range(0, 360, 30):
        gx = r + math.cos(math.radians(a)) * r * 0.8
        gy = r + math.sin(math.radians(a)) * r * 0.8
        pygame.draw.circle(s, (45, 47, 56), (int(gx), int(gy)), max(2, int(r * 0.05)))
    pygame.draw.circle(s, (0, 0, 0, 0), c, int(r * 0.68))
    sp = max(4, int(r * 0.16))
    pygame.draw.line(s, (55, 57, 68), (int(r * 0.3), r), (int(r * 1.7), r), sp)
    pygame.draw.line(s, (55, 57, 68), (r, r), (r, int(r * 1.7)), sp)
    pygame.draw.circle(s, (35, 37, 45), c, int(r * 0.26))
    pygame.draw.circle(s, YELLOW, c, int(r * 0.1))
    mw = max(4, int(r * 0.1))
    pygame.draw.rect(s, YELLOW, (r - mw // 2, int(r * 0.04), mw, int(r * 0.2)), border_radius=2)
    return s


def compute_layout():
    global CONTROL_H, PLAY_H, PLAYER_Y, LEFT_RECT, RIGHT_RECT, WHEEL_C, WHEEL_R, WHEEL_SURF
    CONTROL_H = int(H * (0.27 if control_mode == "wheel" else 0.16))
    PLAY_H = H - CONTROL_H
    PLAYER_Y = PLAY_H - CAR_H - int(PLAY_H * 0.07)
    LEFT_RECT = pygame.Rect(0, PLAY_H, W // 2, CONTROL_H)
    RIGHT_RECT = pygame.Rect(W // 2, PLAY_H, W - W // 2, CONTROL_H)
    WHEEL_R = int(min(CONTROL_H * 0.47, W * 0.3))
    WHEEL_C = (W // 2, PLAY_H + CONTROL_H // 2)
    WHEEL_SURF = build_wheel(WHEEL_R)


class Button:
    def __init__(self, rect, label, color, text_color=WHITE, fnt=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.color = color
        self.text_color = text_color
        self.font = fnt or font_btn

    def hit(self, pos):
        return self.rect.collidepoint(pos)

    def draw(self, surf, selected=True, pulse=0):
        r = self.rect.inflate(pulse, pulse)
        if mouse_pressed and r.collidepoint(mpos):
            r = r.inflate(-6, -6)
        col = self.color if selected else tuple(int(c * 0.4) for c in self.color)
        pygame.draw.rect(surf, BLACK, r.move(0, 4), border_radius=14)
        pygame.draw.rect(surf, col, r, border_radius=14)
        pygame.draw.rect(surf, WHITE if selected else (110, 110, 110), r, width=3, border_radius=14)
        draw_text(surf, self.label, self.font, self.text_color if selected else (190, 190, 190),
                  r.center, outline=None)


def build_buttons():
    global BTN_START, BTN_SETTINGS, BTN_RESTART, BTN_MENU, SB
    bw = int(min(W * 0.7, 360))
    bh = int(max(48, U * 0.14))
    cx = W // 2
    BTN_START = Button((cx - bw // 2, int(H * 0.50), bw, bh), "START GAME", BLUE, fnt=font)
    BTN_SETTINGS = Button((cx - bw // 2, int(H * 0.50) + int(bh * 1.3), bw, bh), "SETTINGS", (90, 90, 110), fnt=font)
    BTN_RESTART = Button((cx - bw // 2, int(H * 0.58), bw, bh), "RESTART", ORANGE, fnt=font)
    BTN_MENU = Button((cx - bw // 2, int(H * 0.58) + int(bh * 1.3), bw, bh), "MENU", (90, 90, 110), fnt=font)
    cw = min(int(W * 0.9), 560)
    left = (W - cw) // 2
    gap = int(cw * 0.03)
    bh2 = int(max(44, min(H * 0.075, 80)))
    third = (cw - 2 * gap) // 3
    half = (cw - gap) // 2
    SB = {}
    for i, name in enumerate(("Easy", "Medium", "Hard")):
        SB[name] = Button((left + i * (third + gap), int(H * 0.22), third, bh2), name, DIFF_COLORS[name])
    SB["buttons"] = Button((left, int(H * 0.41), half, bh2), "Buttons", (40, 110, 220))
    SB["wheel"] = Button((left + half + gap, int(H * 0.41), half, bh2), "Steering Wheel", (40, 110, 220))
    SB["sound"] = Button((left, int(H * 0.60), cw, bh2), "Sound: ON", (40, 170, 90))
    SB["back"] = Button((left, int(H * 0.78), cw, bh2), "BACK", YELLOW, (20, 20, 20), font)


def init_trees():
    TREES.clear()
    n = 7
    for side in (0, 1):
        for i in range(n):
            TREES.append([side, i * (H / float(n)) + random.uniform(-20, 20), random.uniform(0.3, 0.75)])


# ---------------------------------------------------------------- particles and popups
def spawn_part(x, y, vx_, vy_, life, color, size):
    PARTS.append([x, y, vx_, vy_, life, life, color, size])


def update_parts():
    for p in PARTS:
        p[0] += p[2]
        p[1] += p[3]
        p[4] -= 1
    PARTS[:] = [p for p in PARTS if p[4] > 0]


def draw_parts(surf):
    for p in PARTS:
        f = p[4] / float(p[5])
        col = tuple(int(c * (0.35 + 0.65 * f)) for c in p[6])
        pygame.draw.circle(surf, col, (int(p[0]), int(p[1])), max(1, int(p[7] * (0.4 + 0.6 * f))))


def emit_exhaust(px, py, spd, lvl):
    if frame % 2:
        return
    x = px + CAR_W / 2.0 + random.uniform(-3, 3)
    y = py + CAR_H - 2
    col = (170, 170, 170) if lvl < 5 or random.random() < 0.6 else (255, 150, 40)
    spawn_part(x, y, random.uniform(-0.3, 0.3), spd * 0.6 + random.uniform(0, 1.5),
               random.randint(16, 26), col, 3 * CAR_S)


def explode(x, y):
    colors = [(255, 200, 40), (255, 120, 20), (230, 60, 20), (110, 110, 110), (60, 60, 60)]
    for _ in range(70):
        a = random.uniform(0, math.pi * 2)
        sp = random.uniform(2, 9) * HS
        spawn_part(x, y, math.cos(a) * sp, math.sin(a) * sp, random.randint(25, 60),
                   random.choice(colors), random.uniform(3, 9) * CAR_S)


def confetti(x, y):
    colors = [YELLOW, CYAN, (255, 90, 160), (120, 255, 120), WHITE]
    for _ in range(36):
        a = random.uniform(math.pi * 1.1, math.pi * 1.9)
        sp = random.uniform(2, 7) * HS
        spawn_part(x, y, math.cos(a) * sp, math.sin(a) * sp, random.randint(30, 55),
                   random.choice(colors), random.uniform(2, 4) * CAR_S)


def add_pop(text, x, y):
    POPS.append([text, x, y, 50])


# ---------------------------------------------------------------- world rendering
def render_world(cars, speed_lines):
    w = WORLD
    w.fill(GRASS_DARK)
    sh = max(40, int(90 * HS))
    off = int(scroll % (2 * sh))
    for y in range(-2 * sh, H + 2 * sh, 2 * sh):
        pygame.draw.rect(w, GRASS_LIGHT, (0, y + off, W, sh))

    pygame.draw.rect(w, ROAD_GRAY, (ROAD_X, 0, ROAD_W, H))

    kh = max(20, int(36 * HS))
    koff = int(scroll % (2 * kh))
    for idx, y in enumerate(range(-2 * kh, H + 2 * kh, kh)):
        col = (225, 40, 40) if idx % 2 == 0 else WHITE
        pygame.draw.rect(w, col, (ROAD_X, y + koff, KERB_W, kh))
        pygame.draw.rect(w, col, (ROAD_X + ROAD_W - KERB_W, y + koff, KERB_W, kh))

    period = max(40, int(70 * HS))
    doff = int(scroll % period)
    for i in (1, 2):
        x = int(ROAD_X + LANE_W * i)
        for y in range(-period, H + period, period):
            pygame.draw.rect(w, (235, 235, 235), (x - 2, y + doff, 4, period // 2))

    for _ in range(speed_lines):
        x = random.randint(ROAD_X + KERB_W, ROAD_X + ROAD_W - KERB_W)
        y = random.randint(0, H)
        pygame.draw.line(w, (110, 110, 115), (x, y), (x, y + speed * 2.5), 2)

    tr = max(8, min(int(ROAD_X * 0.32), 30))
    for side, y, f in TREES:
        x = int(ROAD_X * f) if side == 0 else int(W - ROAD_X * f)
        y = int(y)
        pygame.draw.circle(w, (15, 80, 25), (x + 4, y + 5), tr)
        pygame.draw.rect(w, (90, 60, 30), (x - 2, y - 2, 5, 8))
        pygame.draw.circle(w, (20, 100, 35), (x, y), tr)
        pygame.draw.circle(w, (45, 150, 55), (x - tr // 4, y - tr // 4), int(tr * 0.6))

    for col, x, y, t in cars:
        blit_car(w, col, x, y, t)
    draw_parts(w)


# ---------------------------------------------------------------- HUD / UI drawing
def draw_gear(surf, c, r, color):
    for i in range(8):
        a = i * math.pi / 4
        p1 = (c[0] + math.cos(a) * r * 0.6, c[1] + math.sin(a) * r * 0.6)
        p2 = (c[0] + math.cos(a) * r * 0.95, c[1] + math.sin(a) * r * 0.95)
        pygame.draw.line(surf, color, p1, p2, max(3, int(r * 0.3)))
    pygame.draw.circle(surf, color, c, int(r * 0.68))
    pygame.draw.circle(surf, PANEL, c, int(r * 0.3))


def gear_geometry():
    r = int(U * 0.055)
    return (W // 2, int(U * 0.03) + r), r


def draw_hud():
    pad = int(U * 0.03)
    pw = int(U * 0.37)
    ph = int(U * 0.22)
    rad = int(U * 0.03)

    # level / speed panel: dark background + bright text, readable at any speed
    pr = pygame.Rect(pad, pad, pw, ph)
    pygame.draw.rect(screen, PANEL, pr, border_radius=rad)
    pygame.draw.rect(screen, YELLOW, pr, width=3, border_radius=rad)
    ix = pr.x + int(pad * 0.7)
    draw_text(screen, "LEVEL %d" % level, font, WHITE, (ix, pr.y + int(pad * 0.4)), anchor="topleft")
    bar_y = pr.y + int(U * 0.105)
    bar_h = max(8, int(U * 0.024))
    total = pw - int(pad * 1.4)
    seg_gap = 2
    seg_w = (total - (MAX_LEVEL - 1) * seg_gap) / float(MAX_LEVEL)
    for i in range(MAX_LEVEL):
        col = YELLOW if i < level else (55, 65, 100)
        pygame.draw.rect(screen, col, (ix + i * (seg_w + seg_gap), bar_y, seg_w, bar_h), border_radius=2)
    kmh = int(speed / HS * 14)
    draw_text(screen, "%d km/h" % kmh, font_s, CYAN, (ix, pr.bottom - int(pad * 0.4)), anchor="bottomleft")

    # score panel
    pr2 = pygame.Rect(W - pad - pw, pad, pw, ph)
    pygame.draw.rect(screen, PANEL, pr2, border_radius=rad)
    pygame.draw.rect(screen, YELLOW, pr2, width=3, border_radius=rad)
    ix2 = pr2.x + int(pad * 0.7)
    draw_text(screen, "SCORE", font_s, (200, 210, 235), (ix2, pr2.y + int(pad * 0.4)), anchor="topleft")
    draw_text(screen, str(int(score)), font, WHITE, (ix2, pr2.y + int(U * 0.075)), anchor="topleft")
    draw_text(screen, "BEST %d" % max(high_score, int(score)), font_s, YELLOW,
              (ix2, pr2.bottom - int(pad * 0.4)), anchor="bottomleft")

    # settings button
    gc, gr = gear_geometry()
    pygame.draw.circle(screen, PANEL, gc, gr + 4)
    pygame.draw.circle(screen, YELLOW, gc, gr + 4, 3)
    draw_gear(screen, gc, gr - 2, WHITE)


def draw_controls():
    panel = pygame.Rect(0, PLAY_H, W, CONTROL_H)
    pygame.draw.rect(screen, (24, 26, 32), panel)
    pygame.draw.line(screen, YELLOW, (0, PLAY_H), (W, PLAY_H), 3)
    live = state == "playing"
    if control_mode == "buttons":
        for rect, name, sign in ((LEFT_RECT, "LEFT", -1), (RIGHT_RECT, "RIGHT", 1)):
            down = live and mouse_pressed and rect.collidepoint(mpos)
            pygame.draw.rect(screen, (95, 100, 125) if down else (55, 58, 74), rect.inflate(-8, -8), border_radius=14)
            cx, cy = rect.center
            s = CONTROL_H * 0.2
            pts = [(cx + sign * s, cy - s * 0.2 - s), (cx + sign * s, cy - s * 0.2 + s), (cx - sign * s, cy - s * 0.2)]
            pygame.draw.polygon(screen, WHITE, pts)
            draw_text(screen, name, font_s, WHITE, (cx, rect.bottom - int(CONTROL_H * 0.2)), outline=None)
    else:
        gap = WHEEL_R + int(U * 0.06)
        s = CONTROL_H * 0.12
        for sign in (-1, 1):
            cx = WHEEL_C[0] + sign * (gap + s)
            pts = [(cx + sign * s, WHEEL_C[1] - s), (cx + sign * s, WHEEL_C[1] + s), (cx - sign * s, WHEEL_C[1])]
            pygame.draw.polygon(screen, (110, 114, 140), pts)
        if wheel_drag:
            pygame.draw.circle(screen, YELLOW, WHEEL_C, WHEEL_R + 4, 3)
        rot = pygame.transform.rotate(WHEEL_SURF, -wheel_angle)
        screen.blit(rot, rot.get_rect(center=WHEEL_C))


def draw_menu():
    shade = pygame.Surface((W, H))
    shade.set_alpha(110)
    screen.blit(shade, (0, 0))
    ty = int(H * 0.22 + math.sin(frame * 0.05) * 6)
    draw_text(screen, "CAR RACING", font_title, YELLOW, (W // 2, ty), ow=3)
    draw_text(screen, "Difficulty: " + difficulty, font_s, WHITE, (W // 2, ty + int(U * 0.12)))
    BTN_START.draw(screen, pulse=int(math.sin(frame * 0.12) * 6))
    BTN_SETTINGS.draw(screen)
    draw_text(screen, "Best: %d" % high_score, font_btn, YELLOW, (W // 2, int(H * 0.88)))


def draw_gameover():
    shade = pygame.Surface((W, H))
    shade.set_alpha(min(170, over_timer * 5))
    screen.blit(shade, (0, 0))
    if over_timer < 8:
        return
    draw_text(screen, "GAME OVER", font_l, RED, (W // 2, int(H * 0.2)), ow=3)
    draw_text(screen, "Score: %d" % int(score), font, WHITE, (W // 2, int(H * 0.2) + int(U * 0.13)))
    draw_text(screen, "Level reached: %d" % level, font_s, CYAN, (W // 2, int(H * 0.2) + int(U * 0.2)))
    if new_record and (frame // 15) % 2 == 0:
        draw_text(screen, "NEW RECORD!", font, YELLOW, (W // 2, int(H * 0.2) + int(U * 0.28)))
    elif not new_record:
        draw_text(screen, "Best: %d" % high_score, font_s, YELLOW, (W // 2, int(H * 0.2) + int(U * 0.28)))
    BTN_RESTART.draw(screen)
    BTN_MENU.draw(screen)


def draw_settings():
    shade = pygame.Surface((W, H))
    shade.set_alpha(215)
    screen.blit(shade, (0, 0))
    draw_text(screen, "SETTINGS", font_l, YELLOW, (W // 2, int(H * 0.09)), ow=3)
    draw_text(screen, "Difficulty", font_btn, WHITE, (W // 2, int(H * 0.185)))
    draw_text(screen, "Controls", font_btn, WHITE, (W // 2, int(H * 0.375)))
    draw_text(screen, "Sound", font_btn, WHITE, (W // 2, int(H * 0.565)))
    for name in ("Easy", "Medium", "Hard"):
        SB[name].draw(screen, selected=(difficulty == name))
    SB["buttons"].draw(screen, selected=(control_mode == "buttons"))
    SB["wheel"].draw(screen, selected=(control_mode == "wheel"))
    SB["sound"].label = "Sound: ON" if sound_on else "Sound: OFF"
    SB["sound"].draw(screen, selected=sound_on)
    SB["back"].label = "RESUME" if settings_return == "playing" else "BACK"
    SB["back"].draw(screen)
    if settings_return == "playing":
        draw_text(screen, "Difficulty applies to your next game", font_s, (200, 210, 235), (W // 2, int(H * 0.9)))


def draw_overlays():
    for p in POPS:
        draw_text(screen, p[0], font_btn, YELLOW, (p[1], p[2]))
    if banner > 0:
        age = 90 - banner
        sc = min(1.0, age / 12.0) if banner > 20 else banner / 20.0
        sc *= 1.0 + 0.08 * math.sin(age * 0.4)
        blit_scaled_text("LEVEL %d!" % level, font_l, YELLOW, (W // 2, int(PLAY_H * 0.3)), max(0.05, sc))
    if state == "countdown":
        phase = min(3, cd_frames // 45)
        label = ("3", "2", "1", "GO!")[phase]
        t = (cd_frames % 45) / 45.0
        blit_scaled_text(label, font_xl, (90, 255, 120) if phase == 3 else WHITE,
                         (W // 2, int(PLAY_H * 0.4)), 1.5 - 0.5 * t)


# ---------------------------------------------------------------- game flow
def start_game():
    global state, score, level, speed, enemies, player_x, vx, tilt, crash_tilt, spawn_dist, next_gap
    global cd_frames, banner, shake, new_record, wheel_angle, cur_diff
    compute_layout()
    cur_diff = dict(DIFFS[difficulty])
    score = 0.0
    level = 1
    speed = cur_diff["base"] * HS
    enemies = []
    PARTS.clear()
    POPS.clear()
    player_x = lane_x(1)
    vx = 0.0
    tilt = 0.0
    crash_tilt = 0.0
    spawn_dist = 0.0
    next_gap = cur_diff["gap"] * HS * 0.5
    cd_frames = 0
    banner = 0
    shake = 0
    new_record = False
    wheel_angle = 0.0
    engine_stop()
    state = "countdown"


def open_settings(ret):
    global state, settings_return, wheel_drag
    settings_return = ret
    state = "settings"
    wheel_drag = False
    engine_stop()


def close_settings():
    global state, cd_frames
    if settings_return == "playing":
        state = "countdown"   # short "1 ... GO!" before the race resumes
        cd_frames = 90
    else:
        state = "menu"


def settings_click(pos):
    global difficulty, control_mode, sound_on
    for name, b in SB.items():
        if not b.hit(pos):
            continue
        play("click")
        if name in DIFFS:
            difficulty = name
        elif name == "buttons":
            control_mode = "buttons"
            compute_layout()
        elif name == "wheel":
            control_mode = "wheel"
            compute_layout()
        elif name == "sound":
            sound_on = not sound_on
            if not sound_on and SOUND_OK:
                pygame.mixer.stop()
            else:
                play("click")
        elif name == "back":
            close_settings()
        return


def wheel_update(pos):
    global wheel_angle
    dx = pos[0] - WHEEL_C[0]
    dy = pos[1] - WHEEL_C[1]
    if math.hypot(dx, dy) < 8:
        return
    ang = math.degrees(math.atan2(dy, dx))
    delta = (ang - wheel_start_ptr + 180) % 360 - 180
    wheel_angle = max(-WHEEL_MAX, min(WHEEL_MAX, wheel_start_ang + delta))


def handle_down(pos):
    global state, wheel_drag, wheel_start_ptr, wheel_start_ang
    if state == "menu":
        if BTN_START.hit(pos):
            play("click")
            start_game()
        elif BTN_SETTINGS.hit(pos):
            play("click")
            open_settings("menu")
    elif state == "settings":
        settings_click(pos)
    elif state == "gameover":
        if over_timer > 30:
            if BTN_RESTART.hit(pos):
                play("click")
                start_game()
            elif BTN_MENU.hit(pos):
                play("click")
                state = "menu"
    elif state in ("playing", "countdown"):
        gc, gr = gear_geometry()
        if state == "playing" and math.hypot(pos[0] - gc[0], pos[1] - gc[1]) <= gr * 1.5:
            play("click")
            open_settings("playing")
            return
        if control_mode == "wheel" and pos[1] >= PLAY_H:
            wheel_drag = True
            wheel_start_ptr = math.degrees(math.atan2(pos[1] - WHEEL_C[1], pos[0] - WHEEL_C[0]))
            wheel_start_ang = wheel_angle


def spawn_enemy():
    near = [e for e in enemies if e["y"] < CAR_H * 2.2]
    occupied = set(e["lane"] for e in near)
    free = [l for l in range(3) if l not in occupied]
    if len(occupied) >= 2 or not free:
        return
    lane = random.choice(free)
    enemies.append(dict(lane=lane, x=lane_x(lane), y=-CAR_H - 10.0, color=random.choice(ENEMY_COLORS), passed=False))
    if not occupied and random.random() < cur_diff["double"]:
        free2 = [l for l in free if l != lane]
        if free2:
            l2 = random.choice(free2)
            enemies.append(dict(lane=l2, x=lane_x(l2), y=-CAR_H - 10.0 - random.uniform(0, CAR_H),
                                color=random.choice(ENEMY_COLORS), passed=False))


def crash():
    global state, shake, over_timer, high_score, new_record, crash_tilt, crash_pt
    play("crash")
    engine_stop()
    shake = 26
    over_timer = 0
    crash_tilt = random.choice((-1, 1)) * random.uniform(15, 35)
    crash_pt = (player_x + CAR_W / 2.0, PLAYER_Y + CAR_H / 2.0)
    explode(*crash_pt)
    new_record = int(score) > high_score and int(score) > 50
    high_score = max(high_score, int(score))
    state = "gameover"


def update_playing():
    global score, level, speed, vx, tilt, player_x, spawn_dist, next_gap, banner, shake
    d = cur_diff
    target = (d["base"] + d["inc"] * (level - 1)) * HS
    speed += (target - speed) * 0.04
    score += speed / HS * 0.085

    new_level = min(MAX_LEVEL, 1 + int(score // LEVEL_SCORE))
    if new_level > level:
        level = new_level
        banner = 90
        shake = 7
        play("levelup")
        engine_set(level)
        confetti(player_x + CAR_W / 2.0, PLAYER_Y)

    # steering: keyboard, touch buttons or wheel
    keys = pygame.key.get_pressed()
    steer = 0.0
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        steer -= 1
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        steer += 1
    if control_mode == "buttons" and mouse_pressed:
        if LEFT_RECT.collidepoint(mpos):
            steer -= 1
        elif RIGHT_RECT.collidepoint(mpos):
            steer += 1
    elif control_mode == "wheel":
        steer += wheel_angle / 90.0
    steer = max(-1.0, min(1.0, steer))

    maxv = LANE_W * 0.085
    vx += (steer * maxv - vx) * 0.22
    player_x += vx
    lo = ROAD_X + KERB_W + 2
    hi = ROAD_X + ROAD_W - KERB_W - CAR_W - 2
    if player_x < lo:
        player_x = lo
        vx = 0
    elif player_x > hi:
        player_x = hi
        vx = 0
    tilt = -vx / maxv * 12.0

    # spawn traffic by distance travelled
    spawn_dist += speed
    if spawn_dist >= next_gap:
        spawn_dist = 0
        gap = max(d["gapmin"], d["gap"] - 14 * (level - 1)) * HS
        next_gap = gap * random.uniform(1.0, 1.5)
        spawn_enemy()

    prect = pygame.Rect(player_x, PLAYER_Y, CAR_W, CAR_H).inflate(-CAR_W * 0.2, -CAR_H * 0.12)
    for e in enemies:
        e["y"] += speed * LANE_MULT[e["lane"]]
        if not e["passed"] and e["y"] > PLAYER_Y + CAR_H:
            e["passed"] = True
            if abs((e["x"] + CAR_W / 2.0) - (player_x + CAR_W / 2.0)) < LANE_W * 0.95:
                score += 25
                play("whoosh")
                add_pop("+25", e["x"] + CAR_W / 2.0, PLAYER_Y)
        erect = pygame.Rect(e["x"], e["y"], CAR_W, CAR_H).inflate(-CAR_W * 0.2, -CAR_H * 0.12)
        if prect.colliderect(erect):
            crash()
            return
    enemies[:] = [e for e in enemies if e["y"] < H + CAR_H]
    emit_exhaust(player_x, PLAYER_Y, speed, level)


# ---------------------------------------------------------------- start
compute_layout()
build_buttons()
init_trees()

running = True
while running:
    frame += 1
    mouse_pressed = pygame.mouse.get_pressed()[0]
    mpos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if state == "playing":
                    open_settings("playing")
                elif state == "settings":
                    close_settings()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            handle_down(event.pos)
        elif event.type == pygame.MOUSEMOTION:
            if wheel_drag:
                wheel_update(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP:
            wheel_drag = False

    # wheel returns to centre when released
    if not wheel_drag:
        wheel_angle *= 0.82
        if abs(wheel_angle) < 0.5:
            wheel_angle = 0.0

    # state updates
    if state == "countdown":
        cd_frames += 1
        if cd_frames in (1, 46, 91):
            play("beep")
        elif cd_frames == 136:
            play("go")
        if cd_frames >= 180:
            state = "playing"
            engine_set(level)
    elif state == "playing":
        update_playing()
    elif state == "gameover":
        over_timer += 1
        if over_timer < 150 and frame % 3 == 0:
            spawn_part(crash_pt[0] + random.uniform(-8, 8), crash_pt[1], random.uniform(-0.5, 0.5),
                       random.uniform(0.5, 1.5), 35, (90, 90, 90), 6 * CAR_S)

    if state == "playing":
        ws = speed
    elif state == "countdown":
        ws = speed * 0.35
    elif state == "menu" or (state == "settings" and settings_return == "menu"):
        ws = 5 * HS
    else:
        ws = 0.0
    scroll += ws
    for t in TREES:
        t[1] += ws
        if t[1] > H + 40:
            t[1] = -40
            t[2] = random.uniform(0.3, 0.75)

    update_parts()
    for p in POPS:
        p[2] -= 1.2
        p[3] -= 1
    POPS[:] = [p for p in POPS if p[3] > 0]
    if banner > 0:
        banner -= 1
    if shake > 0:
        shake -= 1

    # cars to draw
    in_menu_scene = state == "menu" or (state == "settings" and settings_return == "menu")
    cars = []
    if in_menu_scene:
        dx = lane_x(1) + math.sin(frame * 0.03) * LANE_W * 0.9
        dt = -math.cos(frame * 0.03) * 8
        dy = H * 0.68
        cars.append((BLUE, dx, dy, dt))
        emit_exhaust(dx, dy, ws, 1)
    else:
        for e in enemies:
            cars.append((e["color"], e["x"], e["y"], 0))
        cars.append((BLUE, player_x, PLAYER_Y, crash_tilt if state == "gameover" else tilt))

    lines = 0
    if state == "playing" and level >= 3:
        lines = level * 2
    render_world(cars, lines)

    screen.fill(BLACK)
    if shake > 0:
        screen.blit(WORLD, (random.randint(-shake, shake) // 2, random.randint(-shake, shake) // 2))
    else:
        screen.blit(WORLD, (0, 0))

    in_game = state in ("countdown", "playing", "gameover") or (state == "settings" and settings_return == "playing")
    if in_game:
        draw_hud()
        draw_controls()
        draw_overlays()

    if state == "menu":
        draw_menu()
    elif state == "gameover":
        draw_gameover()
    elif state == "settings":
        draw_settings()

    pygame.display.flip()
    clock.tick(60)

engine_stop()
pygame.quit()
