"""Receive the ESP32's fake 8-channel data over UDP and check it.

Run on the Mac (same Wi-Fi as the ESP32):
    python3 receive_fake8.py          # print rate and lost samples once a second
    python3 receive_fake8.py --plot   # also show a live 8-channel plot

Each UDP packet has 10 text lines:  sampleNum,ch1,...,ch8   (values in microvolts).
"""
import argparse                 # reads command-line options like --plot
import socket                   # network sockets: lets Python receive UDP packets
import time                     # clock, for the once-a-second report
from collections import deque   # a list with a max length: old items fall off the front

import numpy as np              # fast number arrays (used for the plot's time axis)

PORT = 12345   # must match UDP_PORT in the ESP32 sketch
FS = 250       # samples per second the ESP32 sends
NUM_CH = 8     # channels per sample


def main():
    # --- command-line options ---
    ap = argparse.ArgumentParser()
    ap.add_argument("--plot", action="store_true", help="show a live plot")              # on/off switch
    ap.add_argument("--seconds", type=float, default=4, help="seconds shown in the plot")
    args = ap.parse_args()                       # read what the user typed

    # --- open the UDP socket ---
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)       # AF_INET = IPv4, SOCK_DGRAM = UDP
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)    # allow restarting right away
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)    # allow two listeners on the same port
    sock.bind(("", PORT))              # listen on port 12345 on every network interface
    sock.settimeout(0.05)              # wait at most 50 ms for a packet, so the plot keeps updating
    print(f"Listening on UDP port {PORT}. Waiting for the ESP32...")

    # --- storage and counters ---
    keep = int(args.seconds * FS)                        # samples to keep for the plot (4 s x 250 = 1000)
    data = [deque(maxlen=keep) for _ in range(NUM_CH)]   # one rolling buffer per channel
    expected = None          # the next sample number we expect (unknown until the first packet)
    lost = got = 0           # samples lost (gaps in numbering) and samples received
    sender = None            # the ESP32's IP address, once we hear from it
    t_report = time.time()   # when we last printed a report
    got_at_report = 0        # `got` at the last report, to work out the rate

    # --- set up the plot window (only with --plot) ---
    if args.plot:
        import matplotlib.pyplot as plt                                  # plotting library
        plt.ion()                                                        # interactive mode: redraw without blocking
        fig, axes = plt.subplots(NUM_CH, 1, sharex=True, figsize=(10, 8))   # 8 stacked plots, one per channel
        lines = [ax.plot([], [], lw=0.8)[0] for ax in axes]             # an empty line in each plot
        for i, ax in enumerate(axes):                                    # label and scale each plot
            ax.set_ylabel(f"ch{i + 1}\nuV", rotation=0, labelpad=20, fontsize=8)
            ax.set_ylim(-40, 40)                                         # +/-40 uV fits every fake wave
            ax.set_xlim(0, args.seconds)                                 # show the last 4 seconds
        axes[-1].set_xlabel("seconds")
        fig.suptitle("ESP32 fake 8-channel data over Wi-Fi")
        fig.tight_layout()
        last_draw = 0                                                    # when we last redrew the plot

    # --- main loop: runs until Ctrl+C (or the plot window is closed) ---
    while True:
        try:
            payload, addr = sock.recvfrom(4096)    # wait for one packet (up to 4096 bytes)
        except socket.timeout:
            payload = None                         # nothing arrived in 50 ms; that's fine

        if payload:
            if sender is None:                     # first packet ever: say who sent it
                sender = addr[0]
                print(f"Receiving from ESP32 at {sender}")
            # Bytes -> text -> separate lines (10 per packet).
            for line in payload.decode(errors="replace").strip().splitlines():
                parts = line.split(",")            # "12,3.4,..." -> ["12", "3.4", ...]
                if len(parts) != NUM_CH + 1:       # must be 1 sample number + 8 values
                    continue                       # skip a damaged line
                n = int(parts[0])                  # the sample number
                if expected is not None and n > expected:
                    lost += n - expected           # a jump (e.g. 299 -> 310) = samples that never arrived
                expected = n + 1                   # next one should be n + 1
                got += 1                           # one more sample received
                for ch in range(NUM_CH):
                    data[ch].append(float(parts[ch + 1]))   # store each channel's value

        now = time.time()
        # --- once a second: print the rate and loss ---
        if now - t_report >= 1:
            rate = (got - got_at_report) / (now - t_report)   # samples received per second
            total = got + lost
            pct = 100 * lost / total if total else 0           # % of samples lost
            print(f"{rate:6.1f} samples/s (expect {FS})   received {got}   lost {lost} ({pct:.2f}%)")
            t_report, got_at_report = now, got                 # start the next 1-second window

        # --- redraw the plot about 10 times a second ---
        if args.plot:
            if data[0] and now - last_draw > 0.1:
                x = np.arange(len(data[0])) / FS               # time axis: 0, 0.004, 0.008 ... seconds
                for ch in range(NUM_CH):
                    lines[ch].set_data(x, list(data[ch]))      # give each line its newest data
                last_draw = now
            plt.pause(0.001)                                   # let the window draw and handle clicks
            if not plt.fignum_exists(fig.number):              # window closed -> stop the program
                break


if __name__ == "__main__":   # only run main() when this file is run directly
    main()
