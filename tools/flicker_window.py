"""
A small always-on-top flicker window to watch SSVEP live in the OpenBCI GUI's FFT plot.

The flicker is locked to the display's frames (60 Hz screen: 15 Hz = 4 frames, 12 Hz = 5 frames).

Usage:
    python live_inference/flicker_window.py --freq 15
Keys: SPACE pause/resume · 1 = 12 Hz · 2 = 15 Hz · 3 = 10 Hz · Esc quit
"""

import argparse
import os
import time

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freq", type=float, default=15)
    ap.add_argument("--size", type=int, default=420)
    ap.add_argument("--x", type=int, default=1010, help="window position on screen (points)")
    ap.add_argument("--y", type=int, default=260)
    args = ap.parse_args()
    os.environ["SDL_VIDEO_WINDOW_POS"] = f"{args.x},{args.y}"
    import pygame

    pygame.init()
    screen = pygame.display.set_mode((args.size, args.size + 40), pygame.SCALED, vsync=1)
    font = pygame.font.SysFont(None, 26)
    stamps = []
    for _ in range(60):
        screen.fill((30, 30, 30))
        pygame.display.flip()
        pygame.event.pump()
        stamps.append(time.perf_counter())
    refresh = 1 / float(np.median(np.diff(stamps)))

    freq, running, k = args.freq, True, 0
    flips = []
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit()
                return
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    running = not running
                elif e.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    freq = {pygame.K_1: 12.0, pygame.K_2: 15.0, pygame.K_3: 10.0}[e.key]
        n = max(2, round(refresh / freq))
        on = running and (k % n) < (n + 1) // 2
        screen.fill((255, 255, 255) if on else (0, 0, 0), (0, 0, args.size, args.size))
        pygame.draw.circle(screen, (255, 0, 0), (args.size // 2, args.size // 2), 6)
        screen.fill((20, 20, 20), (0, args.size, args.size, 40))
        state = f"{refresh / n:.2f} Hz flicker" if running else "PAUSED (rest)"
        label = font.render(f"{state}   ·   space pause · 1/2/3 = 12/15/10 Hz", True, (220, 220, 220))
        screen.blit(label, (10, args.size + 12))
        pygame.display.set_caption(f"Flicker {refresh / n:.1f} Hz" if running else "Flicker paused")
        pygame.display.flip()
        k += 1
        flips.append(time.perf_counter())
        if len(flips) == 600:
            fps = 1 / np.median(np.diff(flips))
            if abs(fps - refresh) > 2:
                print(f"warning: frames running at {fps:.1f} Hz instead of {refresh:.1f} Hz")
            flips = []


if __name__ == "__main__":
    main()
