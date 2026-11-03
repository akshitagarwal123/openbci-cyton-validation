"""Receive the ESP32's fake 8-channel data over UDP and check it.

Run on the Mac (same Wi-Fi as the ESP32):
    python3 receive_fake8.py          # print rate and lost packets once a second
    python3 receive_fake8.py --plot   # also show a live 8-channel plot

Each UDP packet has 10 text lines:  sampleNum,ch1,...,ch8   (values in microvolts).
"""
import argparse
import socket
import time
from collections import deque

import numpy as np

PORT = 12345
FS = 250
NUM_CH = 8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plot", action="store_true", help="show a live plot")
    ap.add_argument("--seconds", type=float, default=4, help="seconds shown in the plot")
    args = ap.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", PORT))              # listen on every network interface
    sock.settimeout(0.05)
    print(f"Listening on UDP port {PORT}. Waiting for the ESP32...")

    keep = int(args.seconds * FS)
    data = [deque(maxlen=keep) for _ in range(NUM_CH)]
    expected = None                   # next sample number we expect
    lost = got = 0
    sender = None
    t_report = time.time()
    got_at_report = 0

    if args.plot:
        import matplotlib.pyplot as plt
        plt.ion()
        fig, axes = plt.subplots(NUM_CH, 1, sharex=True, figsize=(10, 8))
        lines = [ax.plot([], [], lw=0.8)[0] for ax in axes]
        for i, ax in enumerate(axes):
            ax.set_ylabel(f"ch{i + 1}\nuV", rotation=0, labelpad=20, fontsize=8)
            ax.set_ylim(-40, 40)
            ax.set_xlim(0, args.seconds)
        axes[-1].set_xlabel("seconds")
        fig.suptitle("ESP32 fake 8-channel data over Wi-Fi")
        fig.tight_layout()

    while True:
        try:
            payload, addr = sock.recvfrom(4096)
        except socket.timeout:
            payload = None
        if payload:
            if sender is None:
                sender = addr[0]
                print(f"Receiving from ESP32 at {sender}")
            for line in payload.decode(errors="replace").strip().splitlines():
                parts = line.split(",")
                if len(parts) != NUM_CH + 1:
                    continue
                n = int(parts[0])
                if expected is not None and n > expected:
                    lost += n - expected      # a gap = samples that never arrived
                expected = n + 1
                got += 1
                for ch in range(NUM_CH):
                    data[ch].append(float(parts[ch + 1]))

        now = time.time()
        if now - t_report >= 1:
            rate = (got - got_at_report) / (now - t_report)
            total = got + lost
            print(f"{rate:6.1f} samples/s (expect {FS})   received {got}   lost {lost}"
                  f" ({100 * lost / total if total else 0:.2f}%)")
            t_report, got_at_report = now, got
            if args.plot and data[0]:
                x = np.arange(len(data[0])) / FS
                for ch in range(NUM_CH):
                    lines[ch].set_data(x, list(data[ch]))
        if args.plot:
            if data[0] and now - getattr(main, "_last_draw", 0) > 0.1:
                x = np.arange(len(data[0])) / FS
                for ch in range(NUM_CH):
                    lines[ch].set_data(x, list(data[ch]))
                main._last_draw = now
            plt.pause(0.001)
            if not plt.fignum_exists(fig.number):
                break


if __name__ == "__main__":
    main()
