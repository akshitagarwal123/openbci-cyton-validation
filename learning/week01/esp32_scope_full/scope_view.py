"""
Live view of every sample from esp32_scope_full.ino: input (G35) and output (G34) in volts.

Usage (Arduino Serial Monitor/Plotter CLOSED):
    ~/Documents/Projects/BrainTech/.venv/bin/python scope_view.py            # 50 Hz
    ~/Documents/Projects/BrainTech/.venv/bin/python scope_view.py --freq 1000
"""

import argparse
import glob

import matplotlib.pyplot as plt
import numpy as np
import serial


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freq", type=float, default=50, help="sine frequency in Hz (5 to 1000)")
    ap.add_argument("--port", default=(glob.glob("/dev/cu.usbserial*") or [None])[0])
    args = ap.parse_args()

    s = serial.Serial(args.port, 921600, timeout=2)
    s.write(f"{args.freq}\n".encode())

    plt.ion()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    li, = ax.plot([], [], ".-", ms=3, label="input (G35)")
    lo, = ax.plot([], [], ".-", ms=3, label="output (G34)")
    ax.set(xlabel="Time (ms)", ylabel="Volts", ylim=(0, 3.3))
    ax.legend(loc="upper right")
    ax.grid(alpha=0.3)

    while plt.fignum_exists(fig.number):
        line = s.readline().decode(errors="ignore").strip()
        if not line.startswith("frame"):
            continue
        _, f, n = line.split(",")
        n = int(n)
        rows = [s.readline().decode(errors="ignore").strip().split(",") for _ in range(n)]
        try:
            data = np.array(rows, dtype=float) * 3.3 / 4095
        except ValueError:
            continue
        t = np.arange(n) / 10.0                    # 10 samples per ms
        li.set_data(t, data[:, 0])
        lo.set_data(t, data[:, 1])
        ax.set_xlim(0, t[-1])
        gain = np.ptp(data[:, 1]) / np.ptp(data[:, 0])
        ax.set_title(f"{float(f):g} Hz · {n // 2} samples per wave (all of them) · output/input = {gain:.2f}")
        fig.canvas.draw_idle()
        plt.pause(0.01)


if __name__ == "__main__":
    main()
