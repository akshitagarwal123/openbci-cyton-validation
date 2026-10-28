"""
Read one sweep from esp32_bode.ino over USB and plot the measured Bode plot over the theory.

Usage (ESP32 plugged in, sketch uploaded, Arduino Serial Monitor CLOSED):
    .venv/bin/python bode_plot.py --r 10000 --c 0.1e-6
"""

import argparse
import glob

import matplotlib.pyplot as plt
import numpy as np
import serial


def find_port():
    ports = glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/cu.wchusbserial*") + glob.glob("/dev/cu.SLAB*")
    if not ports:
        raise SystemExit("No ESP32 found. Plug it in and close the Arduino Serial Monitor.")
    return ports[0]


def read_sweep(port):
    rows = []
    with serial.Serial(port, 115200, timeout=30) as s:
        print(f"Listening on {port}; waiting for the next sweep...")
        while s.readline().decode(errors="ignore").strip() != "start":
            pass
        s.readline()                                   # header line
        while True:
            line = s.readline().decode(errors="ignore").strip()
            if line == "done" or not line:
                break
            f, g, p = map(float, line.split(","))
            rows.append((f, g, p))
            print(f"  {f:7.1f} Hz   gain {g:.3f} ({20 * np.log10(g):6.1f} dB)   phase {p:6.1f}°")
    return np.array(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--r", type=float, default=10000, help="resistor in ohms")
    ap.add_argument("--c", type=float, default=0.1e-6, help="capacitor in farads")
    ap.add_argument("--port", help="serial port (auto-detected if omitted)")
    args = ap.parse_args()

    data = read_sweep(args.port or find_port())
    fc = 1 / (2 * np.pi * args.r * args.c)
    f = np.logspace(0, 3.2, 400)
    theory_db = 20 * np.log10(1 / np.sqrt(1 + (f / fc) ** 2))
    theory_ph = -np.degrees(np.arctan(f / fc))

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
    a1.semilogx(f, theory_db, label=f"theory (cutoff {fc:.0f} Hz)")
    a1.semilogx(data[:, 0], 20 * np.log10(data[:, 1]), "o", label="measured (ESP32)")
    a1.axhline(-3, color="gray", ls=":")
    a1.set(ylabel="Gain (dB)", title=f"RC low-pass: R = {args.r:g} Ω, C = {args.c:g} F")
    a2.semilogx(f, theory_ph, label="theory")
    a2.semilogx(data[:, 0], data[:, 2], "o", label="measured")
    a2.axhline(-45, color="gray", ls=":")
    a2.set(xlabel="Frequency (Hz)", ylabel="Phase (°)")
    for a in (a1, a2):
        a.grid(True, which="both", alpha=0.3)
        a.legend()
    plt.tight_layout()
    plt.savefig("bode_measured.png", dpi=120)
    print("Saved bode_measured.png")
    plt.show()


if __name__ == "__main__":
    main()
