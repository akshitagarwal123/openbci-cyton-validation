"""
Brain Runner: a turn-based SSVEP game.

A ball rolls down a road. At every fork, a gem sits on one side and a rock on
the other. Two panels flicker: LEFT at 12 Hz, RIGHT at 15 Hz. Look at the panel
on the gem's side; after a few seconds the game reads your visual cortex (CCA on
channel 1 at O1) and steers the ball. Collect gems, avoid rocks.

It reads the OpenBCI GUI's recording file (keep the GUI streaming), so no extra
streaming setup is needed. Every round is logged to runs/ssvep_runner_<time>.csv.

Usage:
    python live_inference/ssvep_runner.py               # 20 rounds, brain control
    python live_inference/ssvep_runner.py --free        # no gem hint: go where you like
    python live_inference/ssvep_runner.py --keyboard    # practise with arrow keys
    python live_inference/ssvep_runner.py --rounds 10 --decide 5

Keys: Esc quits. In brain mode, arrow keys are ignored.
"""

import argparse
import math
import os
import random
import time
from collections import deque
from datetime import datetime

import numpy as np
import pygame
from scipy.signal import butter, iirnotch, sosfiltfilt, filtfilt

from breathing_hr import FS, RAIL_UV
from live_hr import RecordingTail
from ssvep_test import _cca_corr, _make_reference

FREQS = {"left": 12.0, "right": 15.0}
BG, ROAD, LINE, INK, MUTED = (14, 17, 26), (38, 44, 60), (90, 98, 120), (235, 237, 242), (140, 146, 160)
GEM, ROCK, BALL, GOOD, BAD = (80, 200, 255), (150, 120, 95), (255, 196, 64), (90, 210, 120), (240, 90, 80)


class Brain:
    """Keeps a rolling buffer of channel-1 samples from the GUI recording."""

    def __init__(self, channel=1, seconds=12):
        self.tail = RecordingTail(channel)
        self.t = deque(maxlen=FS * seconds)
        self.x = deque(maxlen=FS * seconds)

    def pump(self):
        ts, vals = self.tail.read()
        self.t.extend(ts)
        self.x.extend(vals)
        return self.t[-1] if self.t else 0

    def decide(self, t0, t1):
        t, x = np.asarray(self.t), np.asarray(self.x)
        if len(x) < 4 * FS:
            return None, {}, "no data from the GUI"
        b, a = iirnotch(50, 30, FS)
        y = filtfilt(b, a, sosfiltfilt(butter(4, [5, 45], "bandpass", fs=FS, output="sos"), x - np.median(x)))
        m = (t >= t0) & (t < t1)
        if m.sum() < FS:
            return None, {}, "window not recorded"
        if np.mean(np.abs(x[m]) > RAIL_UV) > 0.05:
            return None, {}, "electrode lost contact"
        w = y[m][None, :]
        scores = {side: _cca_corr(w, _make_reference(f, w.shape[1], FS, 2)) for side, f in FREQS.items()}
        side = max(scores, key=scores.get)
        return side, scores, ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rounds", type=int, default=20)
    ap.add_argument("--decide", type=float, default=4.0, help="seconds of flicker per decision")
    ap.add_argument("--rest", type=float, default=2.0, help="seconds without flicker between rounds")
    ap.add_argument("--free", action="store_true", help="no gem hint; just look where you want to go")
    ap.add_argument("--keyboard", action="store_true", help="choose with arrow keys instead of the brain")
    ap.add_argument("--channel", type=int, default=1)
    args = ap.parse_args()

    pygame.init()
    size = pygame.display.get_desktop_sizes()[0]
    screen = pygame.display.set_mode(size, pygame.FULLSCREEN | pygame.SCALED, vsync=1)
    pygame.display.set_caption("Brain Runner")
    W, H = screen.get_size()
    big, mid, small = (pygame.font.SysFont("helveticaneue", s, bold=b) for s, b in ((64, True), (34, True), (24, False)))

    stamps = []
    for _ in range(60):
        screen.fill(BG)
        pygame.display.flip()
        pygame.event.pump()
        stamps.append(time.perf_counter())
    refresh = 1 / float(np.median(np.diff(stamps)))
    frames = {side: max(2, round(refresh / f)) for side, f in FREQS.items()}

    brain = None if args.keyboard else Brain(args.channel)
    os.makedirs(os.path.join(os.path.dirname(__file__), "runs"), exist_ok=True)
    log_path = os.path.join(os.path.dirname(__file__), "runs", f"ssvep_runner_{datetime.now():%Y%m%d_%H%M%S}.csv")
    log = open(log_path, "w")
    log.write("round,target,choice,correct,score_left_12hz,score_right_15hz,note\n")

    panel_w, panel_h = int(W * 0.26), int(H * 0.5)
    panels = {"left": pygame.Rect(int(W * 0.04), int(H * 0.22), panel_w, panel_h),
              "right": pygame.Rect(W - int(W * 0.04) - panel_w, int(H * 0.22), panel_w, panel_h)}
    road = pygame.Rect(int(W * 0.36), 0, int(W * 0.28), H)

    def quit_check():
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                raise KeyboardInterrupt
            if e.type == pygame.KEYDOWN and args.keyboard and e.key in (pygame.K_LEFT, pygame.K_RIGHT):
                return "left" if e.key == pygame.K_LEFT else "right"
        return None

    def text(s, font, color, center):
        img = font.render(s, True, color)
        screen.blit(img, img.get_rect(center=center))

    def draw_road(scroll, ball_x, target, show_items=True):
        screen.fill(BG)
        pygame.draw.rect(screen, ROAD, road)
        for y in range(-80, H + 80, 80):
            yy = (y + scroll) % (H + 80) - 40
            pygame.draw.rect(screen, LINE, (W // 2 - 4, yy, 8, 40))
        if show_items and target:
            gx = road.left + road.width * (0.22 if target == "left" else 0.78)
            rx = road.left + road.width * (0.78 if target == "left" else 0.22)
            pygame.draw.polygon(screen, GEM, [(gx, H * 0.3 - 30), (gx + 26, H * 0.3), (gx, H * 0.3 + 30), (gx - 26, H * 0.3)])
            pygame.draw.circle(screen, ROCK, (int(rx), int(H * 0.3)), 30)
        pygame.draw.circle(screen, BALL, (int(ball_x), int(H * 0.82)), 26)

    def hud(rnd, score, hits, decided):
        acc = f"{100 * hits / decided:.0f}%" if decided else "–"
        text(f"Round {rnd}/{args.rounds}    Gems {score}    Brain accuracy {acc}", small, MUTED, (W // 2, 28))

    score = hits = decided = 0
    scroll = 0.0
    try:
        # intro
        end = time.time() + 6
        while time.time() < end:
            quit_check()
            if brain:
                brain.pump()
            draw_road(scroll, W // 2, None)
            text("BRAIN RUNNER", big, INK, (W // 2, H * 0.35))
            msg = "Look at the flashing panel on the GEM's side" if not args.free else "Look at the side you want to go"
            text(msg, mid, INK, (W // 2, H * 0.48))
            text("LEFT panel 12 Hz   ·   RIGHT panel 15 Hz   ·   keep your head still", small, MUTED, (W // 2, H * 0.56))
            pygame.display.flip()

        for rnd in range(1, args.rounds + 1):
            target = None if args.free else random.choice(["left", "right"])
            ball_x = W / 2
            # rest: road scrolls, no flicker, so the visual response resets
            end = time.time() + args.rest
            while time.time() < end:
                quit_check()
                scroll += 6
                draw_road(scroll, ball_x, target)
                hud(rnd, score, hits, decided)
                text("get ready…", mid, MUTED, (W // 2, H * 0.62))
                pygame.display.flip()
                if brain:
                    brain.pump()

            # decide: both panels flicker, frame-locked to the display
            k, key_choice = 0, None
            t_start = time.time()
            while time.time() - t_start < args.decide:
                kc = quit_check()
                key_choice = key_choice or kc
                draw_road(scroll, ball_x, target)
                for side, rect in panels.items():
                    n = frames[side]
                    on = (k % n) < (n + 1) // 2
                    pygame.draw.rect(screen, (255, 255, 255) if on else (0, 0, 0), rect)
                    pygame.draw.rect(screen, LINE, rect, 3)
                frac = (time.time() - t_start) / args.decide
                pygame.draw.rect(screen, LINE, (W * 0.3, H * 0.93, W * 0.4, 10), 1)
                pygame.draw.rect(screen, BALL, (W * 0.3, H * 0.93, W * 0.4 * frac, 10))
                hud(rnd, score, hits, decided)
                pygame.display.flip()
                k += 1
                if args.keyboard and key_choice:
                    break
            t_end = time.time()

            # read the brain
            scores, note = {}, ""
            if args.keyboard:
                choice = key_choice
                note = "keyboard" if choice else "no key pressed"
            else:
                wait_until = time.time() + 4
                while brain.pump() < t_end and time.time() < wait_until:
                    quit_check()
                    draw_road(scroll, ball_x, target)
                    hud(rnd, score, hits, decided)
                    text("reading your brain…", mid, INK, (W // 2, H * 0.62))
                    pygame.display.flip()
                choice, scores, note = brain.decide(t_start + 0.5, t_end)
            if choice and target:
                decided += 1
                hits += choice == target
            correct = int(choice == target) if (choice and target) else ""
            s12 = f"{scores['left']:.3f}" if scores else ""
            s15 = f"{scores['right']:.3f}" if scores else ""
            log.write(f"{rnd},{target or ''},{choice or ''},{correct},{s12},{s15},{note}\n")
            log.flush()

            # move the ball and show the outcome
            dest = W / 2 if not choice else road.left + road.width * (0.22 if choice == "left" else 0.78)
            got_gem = bool(choice and target and choice == target)
            if got_gem:
                score += 1
            t0 = time.time()
            while time.time() - t0 < 1.6:
                quit_check()
                p = min(1, (time.time() - t0) / 0.8)
                bx = W / 2 + (dest - W / 2) * (1 - (1 - p) ** 2)
                scroll += 6
                draw_road(scroll, bx, target, show_items=p < 1)
                hud(rnd, score, hits, decided)
                if not choice:
                    text(f"not sure — {note}", mid, MUTED, (W // 2, H * 0.62))
                elif target:
                    text("GEM! +1" if got_gem else "rock…", big, GOOD if got_gem else BAD, (W // 2, H * 0.6))
                else:
                    text(f"you went {choice.upper()}", big, INK, (W // 2, H * 0.6))
                if scores:
                    text(f"12 Hz {scores['left']:.2f}   ·   15 Hz {scores['right']:.2f}", small, MUTED, (W // 2, H * 0.68))
                pygame.display.flip()
                if brain:
                    brain.pump()

        # final screen
        end = time.time() + 8
        while time.time() < end:
            quit_check()
            screen.fill(BG)
            text("FINISHED", big, INK, (W // 2, H * 0.35))
            if decided:
                text(f"{score} gems  ·  brain picked the right side {hits}/{decided} times ({100 * hits / decided:.0f}%)",
                     mid, INK, (W // 2, H * 0.48))
            text("Esc to close", small, MUTED, (W // 2, H * 0.6))
            pygame.display.flip()
    except KeyboardInterrupt:
        pass
    finally:
        log.close()
        pygame.quit()
    if decided:
        print(f"Brain accuracy: {hits}/{decided} ({100 * hits / decided:.0f}%), gems {score}")
    print(f"Round log: {log_path}")


if __name__ == "__main__":
    main()
