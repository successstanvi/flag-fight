import pygame
import random
import math
import numpy as np
import json
import pycountry
from pathlib import Path

from ggttss import get_country_name

# ================= CONFIG =================
FPS = 60
WIDTH, HEIGHT = 540, 960

BASE_DIR = Path(__file__).parent
FLAGS_DIR = BASE_DIR / "flags"
COUNTRY_JSON = BASE_DIR / "countries.json"

RING_RADIUS = int(min(WIDTH, HEIGHT) * 0.33)
RING_THICKNESS = int(RING_RADIUS * 0.9)
INNER_RADIUS = RING_RADIUS - RING_THICKNESS

GAP_COUNT = 1
GAP_DEG = 30
ROT_SPEED = math.radians(20)

BG_COLOR = (30, 155, 255)
RING_COLOR = (0, 0, 0)

BOTTOM_GRAVITY = 260
DAMPING = 0.995
BOUNCE = 0.35
STOP_SPEED = 8

GROUND_Y = HEIGHT - 40
LEFT_WALL = 0
RIGHT_WALL = WIDTH
TOP_WALL = 0
# ==========================================
last5_played = False


class Flag:
    def __init__(self, img, name, pos, vel, r):
        self.img = img
        self.name = name
        self.pos = np.array(pos, float)
        self.vel = np.array(vel, float)
        self.r = r
        self.free = False


def load_country_names():
    with open(COUNTRY_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    mapping = {}
    for region in data.values():
        for c in region:
            mapping[c["country_code"].upper()] = c["country_name"]
    return mapping


def load_flags(center, country_map):
    flags = []
    images = list(FLAGS_DIR.glob("*.png"))
    if not images:
        raise SystemExit("❌ flags folder empty")

    target = int(RING_RADIUS * 0.18)

    for p in images:
        code = p.stem.upper()
         # e.g. "IN", "USA"
        name = get_country_name(code)

        img = pygame.image.load(p).convert_alpha()
        w, h = img.get_size()
        scale = target / max(w, h)
        img = pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
        r = max(img.get_size()) / 2

        for _ in range(100):
            ang = random.random() * 2 * math.pi
            dist = random.uniform(0, INNER_RADIUS - r - 5)
            pos = center + np.array([math.cos(ang) * dist, math.sin(ang) * dist])
            if r < pos[0] < WIDTH - r and r < pos[1] < HEIGHT - r:
                break

        speed = random.uniform(250, 450)
        a = random.random() * 2 * math.pi
        vel = [math.cos(a) * speed, math.sin(a) * speed]

        flags.append(Flag(img, name, pos, vel, r))

    return flags


def main():
    pygame.init()
    pygame.mixer.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Country Flags Battle")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont(None, 42)
    big_font = pygame.font.SysFont(None, 64)
    huge_font = pygame.font.SysFont(None, 96)

    hit_sound = pygame.mixer.Sound("hit.wav")
    hit_sound.set_volume(0.6)

    center = np.array([WIDTH // 2, HEIGHT // 2])
    gap_half = math.radians(GAP_DEG / 2)

    country_map = load_country_names()
    
    voice_subscribe = pygame.mixer.Sound("subscribe.mp3")
    voice_comment = pygame.mixer.Sound("comment.mp3")
    voice_which_country = pygame.mixer.Sound("which_country.mp3")
    voice_last5 = pygame.mixer.Sound("last_5_remaining.mp3")
    voice_luck = pygame.mixer.Sound("luck.mp3")

    # group random start voices
    start_voices = [
        voice_luck,
        voice_subscribe,
        voice_comment,
        voice_which_country
    ]

    while True:
        flags = load_flags(center, country_map)
        gaps = [random.random() * 2 * math.pi for _ in range(GAP_COUNT)]

        # 🔊 RANDOM START VOICE (ONCE PER GAME)
        random.choice(start_voices).play()

        t = 0
        winner = None
        win_time = 0
        countdown = 3
        state = "PLAY"

        last5_played = False   # 🔴 reset every game

        while True:
            dt = clock.tick(FPS) / 1000
            t += dt

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    return

            # ================= PLAY =================
            if state == "PLAY":
                for f in flags:
                    f.pos += f.vel * dt

                inside = [f for f in flags if not f.free]

                # 🔊 LAST 5 FLAGS REMAINING (ONLY ONCE)
                if len(inside) == 5 and not last5_played:
                    voice_last5.play()
                    last5_played = True

                # ❌ no flags left → restart
                if len(inside) == 0:
                    break

                for i in range(len(inside)):
                    for j in range(i + 1, len(inside)):
                        a, b = inside[i], inside[j]
                        d = b.pos - a.pos
                        dist = np.linalg.norm(d)
                        if dist and dist < a.r + b.r:
                            hit_sound.play()
                            n = d / dist
                            overlap = a.r + b.r - dist
                            a.pos -= n * overlap / 2
                            b.pos += n * overlap / 2
                            a.vel, b.vel = b.vel, a.vel

                for f in inside:
                    v = f.pos - center
                    d = np.linalg.norm(v)
                    if d + f.r >= RING_RADIUS:
                        ang = math.atan2(v[1], v[0])
                        escaped = False
                        for g in gaps:
                            ga = (g + ROT_SPEED * t) % (2 * math.pi)
                            diff = (ang - ga + math.pi) % (2 * math.pi) - math.pi
                            if abs(diff) < gap_half:
                                f.free = True
                                escaped = True
                                break
                        if not escaped and d:
                            hit_sound.play()
                            n = v / d
                            f.vel -= 2 * np.dot(f.vel, n) * n
                            f.pos -= n * ((d + f.r) - RING_RADIUS)

                # -------- GRAVITY + WALLS (FIXED) --------
                for f in flags:
                    if f.free:
                        f.vel[1] += BOTTOM_GRAVITY * dt
                        f.vel *= DAMPING

                    # ⬅️ LEFT WALL
                    if f.pos[0] - f.r <= LEFT_WALL and f.vel[0] < 0:
                        f.pos[0] = LEFT_WALL + f.r
                        f.vel[0] = -f.vel[0] * BOUNCE
                        

                    # ➡️ RIGHT WALL
                    if f.pos[0] + f.r >= RIGHT_WALL and f.vel[0] > 0:
                        f.pos[0] = RIGHT_WALL - f.r
                        f.vel[0] = -f.vel[0] * BOUNCE
                        

                    # ⬆️ TOP WALL
                    if f.pos[1] - f.r <= TOP_WALL and f.vel[1] < 0:
                        f.pos[1] = TOP_WALL + f.r
                        f.vel[1] = -f.vel[1] * BOUNCE
                        

                    # ⬇️ GROUND
                    if f.pos[1] + f.r >= GROUND_Y:
                        f.pos[1] = GROUND_Y - f.r
                        if abs(f.vel[1]) > STOP_SPEED:
                            f.vel[1] = -f.vel[1] * BOUNCE
                            
                        else:
                            f.vel[1] = 0
                        f.vel[0] *= 0.98


                if len(inside) == 1:
                    winner = inside[0]
                    state = "WIN"

            # ================= WIN =================
            if state == "WIN":
                win_time += dt
                if win_time > 5:
                    state = "COUNTDOWN"

            # ================= DRAW =================
            screen.fill(BG_COLOR)

            for i in range(360):
                a = math.radians(i)
                skip = False
                for g in gaps:
                    ga = (g + ROT_SPEED * t) % (2 * math.pi)
                    if abs((a - ga + math.pi) % (2 * math.pi) - math.pi) < gap_half:
                        skip = True
                if not skip:
                    x = center[0] + math.cos(a) * RING_RADIUS
                    y = center[1] + math.sin(a) * RING_RADIUS
                    pygame.draw.circle(screen, RING_COLOR, (int(x), int(y)), 4)

            for f in flags:
                screen.blit(f.img, (f.pos[0] - f.img.get_width() / 2,
                                    f.pos[1] - f.img.get_height() / 2))

            if state == "WIN":
                scale = 1 + 0.15 * math.sin(win_time * 5)
                img = pygame.transform.smoothscale(
                    winner.img,
                    (int(winner.img.get_width() * scale),
                     int(winner.img.get_height() * scale))
                )
                screen.blit(big_font.render("WINNER", True, (0, 255, 0)), (center[0] - 100, 60))
                screen.blit(img, (center[0] - img.get_width() / 2,
                                  center[1] - img.get_height() / 2))

                name = big_font.render(winner.name, True, (0, 0, 0))
                screen.blit(name, (center[0] - name.get_width() / 2,
                                   center[1] + img.get_height() / 2 + 20))

            if state == "COUNTDOWN":
                countdown -= dt
                if countdown <= 0:
                    break
                num = huge_font.render(str(int(countdown) + 1), True, (0, 0, 0))
                screen.blit(num, (center[0] - num.get_width() / 2,
                                  center[1] - num.get_height() / 2))

            pygame.display.flip()


if __name__ == "__main__":
    main()