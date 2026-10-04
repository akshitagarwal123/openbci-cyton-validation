#!/usr/bin/env python3
"""
SSVEP Signal Tester — Observe your brain's response to flickering stimuli.

Shows a large flickering area and prints real-time CCA values.
Use number keys to switch frequencies. Watch the terminal to see
if your brain responds.

Usage:
    python ssvep_test.py --serial-port /dev/cu.usbserial-XXXX
    python ssvep_test.py --synthetic   # test without hardware
"""

import argparse
import threading
import time

import numpy as np
import pygame
from scipy.linalg import svd, inv, sqrtm
from scipy.signal import butter, filtfilt

# ── Configuration ──

FPS = 60
SCREEN_W, SCREEN_H = 1000, 700
BUFFER_SEC = 3.0
N_HARMONICS = 2
BANDPASS = (5, 45)

# Frequencies to test (press 1-6 to switch, 0 for no flicker)
TEST_FREQS = {
    pygame.K_1: ("6 Hz",  6.0),
    pygame.K_2: ("8 Hz",  8.0),
    pygame.K_3: ("10 Hz", 10.0),
    pygame.K_4: ("12 Hz", 12.0),
    pygame.K_5: ("15 Hz", 15.0),
    pygame.K_6: ("20 Hz", 20.0),
    pygame.K_0: ("OFF",   0.0),
}

# All frequencies to compute CCA for (always computed regardless of stimulus)
ALL_FREQS = [6.0, 8.0, 10.0, 12.0, 15.0, 20.0]


# ── CCA ──

def _cca_corr(X, Y):
    n = X.shape[1]
    X = X - X.mean(axis=1, keepdims=True)
    Y = Y - Y.mean(axis=1, keepdims=True)
    Cxx = (X @ X.T) / (n - 1) + np.eye(X.shape[0]) * 1e-6
    Cyy = (Y @ Y.T) / (n - 1) + np.eye(Y.shape[0]) * 1e-6
    Cxy = (X @ Y.T) / (n - 1)
    try:
        Cxx_isqrt = inv(sqrtm(Cxx)).real
        Cyy_isqrt = inv(sqrtm(Cyy)).real
        M = Cxx_isqrt @ Cxy @ Cyy_isqrt
        _, s, _ = svd(M, full_matrices=False)
        return float(np.max(s))
    except Exception:
        return 0.0


def _make_reference(freq, n_samples, sfreq, n_harmonics):
    t = np.arange(n_samples) / sfreq
    refs = []
    for h in range(1, n_harmonics + 1):
        refs.append(np.sin(2 * np.pi * h * freq * t))
        refs.append(np.cos(2 * np.pi * h * freq * t))
    return np.array(refs)


class SignalBuffer:
    def __init__(self, sfreq, n_channels):
        self.sfreq = sfreq
        self.buffer_size = int(BUFFER_SEC * sfreq)
        self.buffer = np.zeros((n_channels, self.buffer_size))
        self.buffer_pos = 0
        self.samples_collected = 0
        nyq = sfreq / 2
        low = max(BANDPASS[0] / nyq, 0.01)
        high = min(BANDPASS[1] / nyq, 0.99)
        self.b, self.a = butter(4, [low, high], btype="band")
        self.lock = threading.Lock()

        # Pre-compute references for all test frequencies
        self.references = {}
        for freq in ALL_FREQS:
            self.references[freq] = _make_reference(
                freq, self.buffer_size, sfreq, N_HARMONICS)

    def add_data(self, data):
        with self.lock:
            n_new = data.shape[1]
            if n_new >= self.buffer_size:
                self.buffer = data[:, -self.buffer_size:]
                self.buffer_pos = 0
            else:
                end = self.buffer_pos + n_new
                if end <= self.buffer_size:
                    self.buffer[:, self.buffer_pos:end] = data
                else:
                    first = self.buffer_size - self.buffer_pos
                    self.buffer[:, self.buffer_pos:] = data[:, :first]
                    self.buffer[:, :n_new - first] = data[:, first:]
                self.buffer_pos = end % self.buffer_size
            self.samples_collected += n_new

    def get_cca_all(self):
        if self.samples_collected < self.buffer_size:
            return {}
        with self.lock:
            data = np.roll(self.buffer, -self.buffer_pos, axis=1).copy()
        try:
            filtered = filtfilt(self.b, self.a, data, axis=1).astype(np.float32)
        except Exception:
            return {}
        result = {}
        for freq, ref in self.references.items():
            result[freq] = _cca_corr(filtered, ref)
        return result


def eeg_thread_func(board, eeg_channels, buf, stop_event):
    while not stop_event.is_set():
        try:
            data = board.get_board_data()
            if data.shape[1] > 0:
                buf.add_data(data[eeg_channels])
        except Exception:
            pass
        time.sleep(0.05)


def main():
    parser = argparse.ArgumentParser(description="SSVEP Signal Tester")
    parser.add_argument("--serial-port", type=str, default=None)
    parser.add_argument("--board-id", type=int, default=0)
    parser.add_argument("--detect-channels", type=str, default="1,2,3")
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()

    from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

    if args.synthetic:
        args.board_id = BoardIds.SYNTHETIC_BOARD.value
        args.serial_port = None

    params = BrainFlowInputParams()
    if args.serial_port:
        params.serial_port = args.serial_port

    BoardShim.disable_board_logger()
    board = BoardShim(args.board_id, params)
    sfreq = BoardShim.get_sampling_rate(args.board_id)
    eeg_channels = BoardShim.get_eeg_channels(args.board_id)
    detect_indices = [int(x.strip()) - 1 for x in args.detect_channels.split(",")]
    detect_eeg_chs = [eeg_channels[i] for i in detect_indices]

    print(f"Connecting (sfreq={sfreq}Hz, channels={detect_indices})...")
    board.prepare_session()
    board.start_stream()
    time.sleep(1)
    board.get_board_data()

    buf = SignalBuffer(sfreq, len(detect_indices))
    stop_event = threading.Event()
    t = threading.Thread(target=eeg_thread_func,
                         args=(board, detect_eeg_chs, buf, stop_event),
                         daemon=True)
    t.start()

    # ── Pygame display ──
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("SSVEP Signal Tester")
    clock = pygame.time.Clock()
    font_large = pygame.font.SysFont("Helvetica", 36, bold=True)
    font_med = pygame.font.SysFont("Helvetica", 22)
    font_small = pygame.font.SysFont("Helvetica", 16)

    active_freq = 0.0
    active_label = "OFF"
    frame_count = 0
    last_cca_time = 0

    print("\n" + "=" * 60)
    print("  SSVEP SIGNAL TESTER")
    print("=" * 60)
    print()
    print("  Press keys to switch flicker frequency:")
    print("    1=6Hz  2=8Hz  3=10Hz  4=12Hz  5=15Hz  6=20Hz  0=OFF")
    print()
    print("  Look at the flickering area and watch the CCA values.")
    print("  The frequency you're looking at should have the HIGHEST value.")
    print("  Press ESC to quit.")
    print()
    print("  " + "-" * 56)
    print(f"  {'':>8s}  {'6Hz':>6s}  {'8Hz':>6s}  {'10Hz':>6s}  "
          f"{'12Hz':>6s}  {'15Hz':>6s}  {'20Hz':>6s}")
    print("  " + "-" * 56)

    running = True
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    elif event.key in TEST_FREQS:
                        active_label, active_freq = TEST_FREQS[event.key]
                        print(f"\n  >>> Switched to {active_label} <<<\n")
                        print(f"  {'':>8s}  {'6Hz':>6s}  {'8Hz':>6s}  "
                              f"{'10Hz':>6s}  {'12Hz':>6s}  {'15Hz':>6s}  "
                              f"{'20Hz':>6s}")

            # ── Draw ──
            screen.fill((0, 0, 0))

            # Flicker area (large rectangle in center)
            if active_freq > 0:
                half_period = FPS / (2 * active_freq)
                is_on = (int(frame_count / half_period) % 2) == 0
                if is_on:
                    flicker_rect = (100, 100, SCREEN_W - 200, SCREEN_H - 250)
                    pygame.draw.rect(screen, (255, 255, 255), flicker_rect)

            # Info bar at bottom
            info_bg = (20, 20, 35)
            pygame.draw.rect(screen, info_bg, (0, SCREEN_H - 130, SCREEN_W, 130))

            # Current frequency
            freq_text = f"Stimulus: {active_label}"
            if active_freq > 0:
                freq_text += f" ({active_freq:.0f} Hz)"
            txt = font_large.render(freq_text, True, (0, 255, 120))
            screen.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2,
                              SCREEN_H - 120))

            # Key hints
            hint = "Keys: 1=6Hz  2=8Hz  3=10Hz  4=12Hz  5=15Hz  6=20Hz  0=OFF  ESC=quit"
            ht = font_small.render(hint, True, (100, 100, 120))
            screen.blit(ht, (SCREEN_W // 2 - ht.get_width() // 2,
                             SCREEN_H - 30))

            # Show "LOOK HERE" when active
            if active_freq > 0:
                look_txt = font_med.render("LOOK AT THIS AREA", True,
                                           (0, 0, 0) if is_on else (100, 100, 100))
                screen.blit(look_txt, (SCREEN_W // 2 - look_txt.get_width() // 2,
                                       SCREEN_H // 2 - 80))

            pygame.display.flip()
            frame_count += 1
            clock.tick(FPS)

            # ── CCA every 0.8 seconds ──
            now = time.time()
            if now - last_cca_time >= 0.8:
                last_cca_time = now
                cca = buf.get_cca_all()
                if cca:
                    parts = []
                    best_freq = max(cca, key=cca.get)
                    for freq in ALL_FREQS:
                        val = cca[freq]
                        marker = " *" if freq == best_freq else "  "
                        parts.append(f"{val:.3f}{marker}")
                    stim = f"[{active_label:>4s}]"
                    print(f"  {stim:>8s}  {'  '.join(parts)}")

    except KeyboardInterrupt:
        pass
    finally:
        print("\n\nShutting down...")
        stop_event.set()
        t.join(timeout=2)
        pygame.quit()
        board.stop_stream()
        board.release_session()


if __name__ == "__main__":
    main()
