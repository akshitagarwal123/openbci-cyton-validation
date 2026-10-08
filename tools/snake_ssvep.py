"""
Brain Snake: turn-based snake steered by SSVEP.

The snake moves a few cells, then pauses. Two panels flicker: LEFT 12 Hz and
RIGHT 15 Hz. Look at one to turn the snake left or right (relative to where it
is heading). If neither response is clearly stronger, the snake keeps going
straight. Eat the food; don't run into yourself. Walls wrap around.

Reads channel 1 (electrode at O1) from the OpenBCI GUI's recording file, so keep
the GUI streaming. Every decision is logged to runs/snake_ssvep_<time>.csv.

Usage:
    python live_inference/snake_ssvep.py
    python live_inference/snake_ssvep.py --keyboard       # arrow keys (practice)
    python live_inference/snake_ssvep.py --steps 3 --decide 4
    python live_inference/snake_ssvep.py --reuse-calibration   # skip the 35-s calibration

The game starts with a short calibration (look left 3x, right 3x) so it learns
your own 12 Hz / 15 Hz response pattern; decisions then use the nearest pattern,
which cancels the 12 Hz bias and a weaker 15 Hz response.
Keys: Esc quits.
"""

import argparse
import json
import os
import random
import time
from datetime import datetime

import numpy as np
import pygame

from ssvep_runner import Brain

BG, GRID, INK, MUTED = (14, 17, 26), (28, 33, 46), (235, 237, 242), (140, 146, 160)
SNAKE, HEAD, FOOD, GOOD, BAD = (90, 210, 120), (160, 240, 170), (255, 120, 90), (90, 210, 120), (240, 90, 80)
DIRS = [(1, 0), (0, 1), (-1, 0), (0, -1)]  # right, down, left, up (clockwise)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--steps", type=int, default=3, help="cells moved between decisions")
    ap.add_argument("--decide", type=float, default=4.0, help="seconds of flicker per decision")
    ap.add_argument("--confidence", type=float, default=0.15,
                    help="0-0.5: how far toward one calibrated pattern the scores must be to turn")
    ap.add_argument("--reuse-calibration", action="store_true", help="use the last saved calibration")
    ap.add_argument("--calib-trials", type=int, default=3, help="calibration looks per side")
    ap.add_argument("--keyboard", action="store_true")
    ap.add_argument("--channel", type=int, default=1)
    args = ap.parse_args()

    pygame.init()
    size = pygame.display.get_desktop_sizes()[0]
    screen = pygame.display.set_mode(size, pygame.FULLSCREEN | pygame.SCALED, vsync=1)
    W, H = screen.get_size()
    big, mid, small = (pygame.font.SysFont("helveticaneue", s, bold=b) for s, b in ((60, True), (32, True), (22, False)))

    stamps = []
    for _ in range(60):
        screen.fill(BG)
        pygame.display.flip()
        pygame.event.pump()
        stamps.append(time.perf_counter())
    refresh = 1 / float(np.median(np.diff(stamps)))
    frames = {"left": max(2, round(refresh / 12)), "right": max(2, round(refresh / 15))}

    cols, rows = 16, 12
    cell = int(min(W * 0.42 / cols, H * 0.78 / rows))
    board = pygame.Rect((W - cols * cell) // 2, (H - rows * cell) // 2 + 20, cols * cell, rows * cell)
    pw, ph = int(W * 0.2), int(H * 0.46)
    panels = {"left": pygame.Rect(int(W * 0.03), (H - ph) // 2, pw, ph),
              "right": pygame.Rect(W - int(W * 0.03) - pw, (H - ph) // 2, pw, ph)}

    brain = None if args.keyboard else Brain(args.channel)
    os.makedirs(os.path.join(os.path.dirname(__file__), "runs"), exist_ok=True)
    log_path = os.path.join(os.path.dirname(__file__), "runs", f"snake_ssvep_{datetime.now():%Y%m%d_%H%M%S}.csv")
    log = open(log_path, "w")
    log.write("decision,choice,score_left_12hz,score_right_15hz,note,length\n")

    def events():
        key = None
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                raise KeyboardInterrupt
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP):
                key = {pygame.K_LEFT: "left", pygame.K_RIGHT: "right", pygame.K_UP: "straight"}[e.key]
        return key

    def text(s, font, color, center):
        img = font.render(s, True, color)
        screen.blit(img, img.get_rect(center=center))

    def draw(snake, food, d, status="", status_color=INK, flicker_k=None, frac=None, highlight=None):
        screen.fill(BG)
        pygame.draw.rect(screen, GRID, board)
        for i, (x, y) in enumerate(snake):
            r = pygame.Rect(board.left + x * cell + 2, board.top + y * cell + 2, cell - 4, cell - 4)
            pygame.draw.rect(screen, HEAD if i == 0 else SNAKE, r, border_radius=6)
        fx, fy = food
        pygame.draw.circle(screen, FOOD, (board.left + fx * cell + cell // 2, board.top + fy * cell + cell // 2), cell // 3)
        hx, hy = snake[0]
        cx, cy = board.left + hx * cell + cell // 2, board.top + hy * cell + cell // 2
        pygame.draw.line(screen, BG, (cx, cy), (cx + d[0] * cell // 3, cy + d[1] * cell // 3), 4)
        for side, rect in panels.items():
            if flicker_k is None:
                pygame.draw.rect(screen, (40, 40, 48), rect)
            else:
                n = frames[side]
                pygame.draw.rect(screen, (255, 255, 255) if (flicker_k % n) < (n + 1) // 2 else (0, 0, 0), rect)
            pygame.draw.rect(screen, HEAD if side == highlight else MUTED, rect, 8 if side == highlight else 2)
            text("TURN LEFT  12 Hz" if side == "left" else "TURN RIGHT  15 Hz", small, MUTED, (rect.centerx, rect.bottom + 22))
        text(f"Length {len(snake)}", small, MUTED, (W // 2, 26))
        if frac is not None:
            pygame.draw.rect(screen, MUTED, (board.left, board.bottom + 14, board.width, 8), 1)
            pygame.draw.rect(screen, HEAD, (board.left, board.bottom + 14, board.width * frac, 8))
        if status:
            text(status, mid, status_color, (W // 2, board.top - 30))
        pygame.display.flip()

    def new_food(snake):
        free = [(x, y) for x in range(cols) for y in range(rows) if (x, y) not in snake]
        return random.choice(free)

    calib_path = os.path.join(os.path.dirname(__file__), "runs", "ssvep_calibration.json")

    def flicker_and_read(snake, food, d, status, highlight=None):
        k, t_start = 0, time.time()
        while time.time() - t_start < args.decide:
            events()
            draw(snake, food, d, status, MUTED, flicker_k=k, frac=(time.time() - t_start) / args.decide,
                 highlight=highlight)
            k += 1
        t_end = time.time()
        wait = time.time() + 4
        while brain.pump() < t_end and time.time() < wait:
            events()
            draw(snake, food, d, "reading your brain…")
        return brain.decide(t_start + 0.5, t_end)

    def calibrate(snake, food, d):
        pts = {"left": [], "right": []}
        order = ["left", "right"] * args.calib_trials
        random.shuffle(order)
        for i, side in enumerate(order, 1):
            t0 = time.time()
            while time.time() - t0 < 2.0:
                events()
                brain.pump()
                draw(snake, food, d, f"Calibration {i}/{len(order)}: get ready to look {side.upper()}", INK,
                     highlight=side)
            _, sc, note = flicker_and_read(snake, food, d, f"look at the {side.upper()} panel", highlight=side)
            if sc:
                pts[side].append([sc["left"], sc["right"]])
        if not pts["left"] or not pts["right"]:
            return None
        cal = {"left": np.mean(pts["left"], axis=0).tolist(), "right": np.mean(pts["right"], axis=0).tolist(),
               "points": pts, "time": datetime.now().isoformat(timespec="seconds")}
        ok = sum(classify(cal, {"left": a, "right": b})[0] == side for side in pts for a, b in pts[side])
        cal["self_accuracy"] = ok / sum(len(v) for v in pts.values())
        json.dump(cal, open(calib_path, "w"), indent=1)
        return cal

    def classify(cal, scores):
        """Project the scores onto the line from the LEFT pattern to the RIGHT pattern: -0.5 = left, +0.5 = right."""
        cl, cr, s_ = np.array(cal["left"]), np.array(cal["right"]), np.array([scores["left"], scores["right"]])
        axis = cr - cl
        pos = float(np.dot(s_ - (cl + cr) / 2, axis) / max(np.dot(axis, axis), 1e-9))
        side = "right" if pos > 0 else "left"
        return side, pos

    snake = [(cols // 2 - i, rows // 2) for i in range(3)]
    di = 0
    food = new_food(snake)
    decision = 0
    try:
        end = time.time() + 6
        while time.time() < end:
            events()
            if brain:
                brain.pump()
            draw(snake, food, DIRS[di], "Look at a flashing panel to turn · nothing clear = straight")
        cal = None
        if brain:
            if args.reuse_calibration and os.path.exists(calib_path):
                cal = json.load(open(calib_path))
            else:
                cal = calibrate(snake, food, DIRS[di])
            if cal:
                t0 = time.time()
                while time.time() - t0 < 4:
                    events()
                    brain.pump()
                    draw(snake, food, DIRS[di], f"Calibrated: it recognised {100 * cal['self_accuracy']:.0f}% of your looks. Go!", GOOD)
                log.write(f"0,calibration,{cal['left'][0]:.3f}/{cal['left'][1]:.3f},{cal['right'][0]:.3f}/{cal['right'][1]:.3f},"
                          f"left pattern / right pattern (12Hz/15Hz),{cal['self_accuracy']:.2f}\n")
        alive = True
        while alive:
            # move a few cells
            for _ in range(args.steps):
                t0 = time.time()
                while time.time() - t0 < 0.35:
                    events()
                    draw(snake, food, DIRS[di])
                if brain:
                    brain.pump()
                dx, dy = DIRS[di]
                head = ((snake[0][0] + dx) % cols, (snake[0][1] + dy) % rows)
                if head in snake[:-1]:
                    alive = False
                    break
                snake.insert(0, head)
                if head == food:
                    food = new_food(snake)
                else:
                    snake.pop()
            if not alive:
                break

            # decide: flicker both panels
            decision += 1
            k, key = 0, None
            t_start = time.time()
            while time.time() - t_start < args.decide:
                key = events() or key
                draw(snake, food, DIRS[di], "look LEFT or RIGHT to turn", MUTED, flicker_k=k,
                     frac=(time.time() - t_start) / args.decide)
                k += 1
                if args.keyboard and key:
                    break
            t_end = time.time()

            scores, note = {}, ""
            if args.keyboard:
                choice = key or "straight"
                note = "keyboard"
            else:
                wait = time.time() + 4
                while brain.pump() < t_end and time.time() < wait:
                    events()
                    draw(snake, food, DIRS[di], "reading your brain…")
                side, scores, note = brain.decide(t_start + 0.5, t_end)
                choice = "straight"
                if scores and cal:
                    side, pos = classify(cal, scores)
                    # a turn also needs a real response: at least half of what that side gave in calibration
                    own = scores["left"] if side == "left" else scores["right"]
                    floor = 0.5 * (cal["left"][0] if side == "left" else cal["right"][1])
                    note = f"pos {pos:+.2f}"
                    if abs(pos) >= args.confidence and own >= floor:
                        choice = side
                    else:
                        note += " (weak response)" if own < floor else " (not confident)"
                elif scores and abs(scores["left"] - scores["right"]) >= 0.12:
                    choice = side
            if choice == "left":
                di = (di - 1) % 4
            elif choice == "right":
                di = (di + 1) % 4
            s12 = f"{scores['left']:.3f}" if scores else ""
            s15 = f"{scores['right']:.3f}" if scores else ""
            log.write(f"{decision},{choice},{s12},{s15},{note},{len(snake)}\n")
            log.flush()

            t0 = time.time()
            while time.time() - t0 < 0.9:
                events()
                msg = {"left": "← LEFT", "right": "RIGHT →", "straight": "↑ straight"}[choice]
                if scores:
                    msg += f"   (12 Hz {scores['left']:.2f} · 15 Hz {scores['right']:.2f})"
                draw(snake, food, DIRS[di], msg, GOOD if choice != "straight" else MUTED)

        end = time.time() + 6
        while time.time() < end:
            events()
            screen.fill(BG)
            text("GAME OVER", big, BAD, (W // 2, H * 0.38))
            text(f"Length {len(snake)} after {decision} brain decisions", mid, INK, (W // 2, H * 0.5))
            pygame.display.flip()
    except KeyboardInterrupt:
        pass
    finally:
        log.close()
        pygame.quit()
    print(f"Length {len(snake)} after {decision} decisions. Log: {log_path}")


if __name__ == "__main__":
    main()
