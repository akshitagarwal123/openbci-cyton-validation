"""
Week 1 exercise: RC low-pass and high-pass filters.

Step 1 of the learning loop (calculate -> simulate -> build -> measure -> compare).
Pick R and C, compute the cutoff, and plot the frequency response so you know
what LTspice and the breadboard should show.

Usage:
    .venv/bin/python hw_learning/week01_rc_filter.py --r 10000 --c 1e-6
"""

import argparse

import matplotlib.pyplot as plt
import numpy as np


def cutoff_hz(r, c):
    return 1 / (2 * np.pi * r * c)


def response(f, r, c, kind):
    """Gain |Vout/Vin| of a first-order RC filter at frequencies f."""
    x = 2 * np.pi * f * r * c
    if kind == "lowpass":
        return 1 / np.sqrt(1 + x**2)
    return x / np.sqrt(1 + x**2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--r", type=float, default=10_000, help="resistance in ohms")
    parser.add_argument("--c", type=float, default=1e-6, help="capacitance in farads")
    args = parser.parse_args()

    fc = cutoff_hz(args.r, args.c)
    tau = args.r * args.c
    print(f"R = {args.r:g} ohm, C = {args.c:g} F")
    print(f"Time constant tau = RC = {tau * 1000:.2f} ms")
    print(f"Cutoff frequency  = {fc:.2f} Hz (gain = 0.707, i.e. -3 dB)")

    # EEG bands for intuition: what a filter at this cutoff keeps or removes.
    for name, f in [("delta", 2), ("alpha", 10), ("beta", 20), ("mains", 50)]:
        lp = response(np.array(f), args.r, args.c, "lowpass")
        print(f"  {name:6s} {f:3d} Hz -> low-pass keeps {lp * 100:5.1f} %, high-pass keeps {(np.sqrt(1 - lp**2)) * 100:5.1f} %")

    f = np.logspace(-1, 3, 500)
    fig, ax = plt.subplots(figsize=(8, 4))
    for kind in ("lowpass", "highpass"):
        ax.semilogx(f, 20 * np.log10(response(f, args.r, args.c, kind)), label=kind)
    ax.axvline(fc, color="gray", ls="--", label=f"cutoff {fc:.1f} Hz")
    ax.axhline(-3, color="gray", ls=":")
    ax.set(xlabel="Frequency (Hz)", ylabel="Gain (dB)", title="RC filter response", ylim=(-40, 3))
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
