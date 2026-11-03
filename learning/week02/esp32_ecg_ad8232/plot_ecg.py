"""Plot your ECG from the ESP32 + AD8232, live, and work out your heart rate.

Run (laptop on BATTERY, charger unplugged):
    python3 plot_ecg.py                      # live plot; close the window to stop and save
    python3 plot_ecg.py --record 30          # no live plot: record 30 s, then save the plot + CSV

Close the Arduino Serial Monitor first (only one program can open the port).
Saves ecg_<time>.csv (all samples) and ecg_<time>.png (the last 10 s, raw and filtered).
Needs: pip install pyserial numpy scipy matplotlib
"""
import argparse
import glob
import time
from collections import deque

import numpy as np
import serial                                   # pyserial: read the ESP32's USB serial port
from scipy import signal

FS = 250          # samples per second (must match SAMPLE_RATE in the sketch)
MAINS_HZ = 50     # mains hum frequency in India (60 in the US)
SHOW_S = 5        # seconds shown in the live plot


def make_filters():
    """Band-pass 0.5-40 Hz (removes slow baseline drift and fast noise) + a notch at the mains hum."""
    bp = signal.butter(2, [0.5, 40], btype="bandpass", fs=FS, output="sos")
    b, a = signal.iirnotch(MAINS_HZ, Q=30, fs=FS)
    return np.vstack([bp, signal.tf2sos(b, a)])


def heart_rate(x):
    """Beats per minute from the R peaks (the tall spikes) in a filtered ECG, or None."""
    if len(x) < 3 * FS:
        return None
    x = x - np.median(x)
    if abs(x.min()) > abs(x.max()):       # electrodes swapped? the R peaks point down; flip them
        x = -x
    peaks, _ = signal.find_peaks(x, height=0.5 * x.max(), distance=int(0.3 * FS))   # max 200 bpm
    if len(peaks) < 2:
        return None
    return 60 * FS / np.median(np.diff(peaks))      # samples between beats -> beats per minute


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=None, help="serial port (default: the first /dev/cu.usbserial*)")
    ap.add_argument("--record", type=float, default=0, help="record N seconds without a live plot")
    args = ap.parse_args()

    port = args.port or (sorted(glob.glob("/dev/cu.usbserial*")) or [None])[0]
    if port is None:
        raise SystemExit("No ESP32 found. Plug it in, or pass --port.")
    ser = serial.Serial(port, 115200, timeout=0.1)
    ser.reset_input_buffer()
    print(f"Reading ECG from {port} at {FS} Hz. "
          + (f"Recording {args.record:.0f} s..." if args.record else "Close the plot window to stop."))

    sos = make_filters()
    zi = signal.sosfilt_zi(sos) * 0            # filter memory, so the live filter runs sample by sample
    raw_all, off_all = [], []                  # everything, for the CSV
    keep = SHOW_S * FS
    raw_buf, filt_buf = deque(maxlen=keep), deque(maxlen=keep)
    hr_buf = deque(maxlen=8 * FS)              # last 8 s of filtered data for the heart rate
    pending = b""

    def read_samples():
        """Read whatever has arrived; return new (millivolts, leadsOff) pairs."""
        nonlocal pending
        pending += ser.read(ser.in_waiting or 1)
        *lines, pending = pending.split(b"\n")
        out = []
        for line in lines:
            try:
                mv, off = line.decode().strip().split(",")
                out.append((float(mv), int(off)))
            except ValueError:
                pass                           # half a line at start-up, or a boot message
        return out

    if not args.record:
        import matplotlib.pyplot as plt
        plt.ion()
        fig, (ax_raw, ax_f) = plt.subplots(2, 1, sharex=True, figsize=(11, 6))
        t = np.arange(keep) / FS
        line_raw, = ax_raw.plot([], [], lw=0.8, color="gray")
        line_f, = ax_f.plot([], [], lw=1.0, color="crimson")
        ax_raw.set_ylabel("raw ADC (mV)")
        ax_f.set_ylabel("filtered (mV)")
        ax_f.set_xlabel("seconds")
        ax_raw.set_xlim(0, SHOW_S)
        title = fig.suptitle("ECG")
        fig.tight_layout()
        last_draw = 0

    start = time.time()
    try:
        while True:
            new = read_samples()
            for mv, off in new:
                raw_all.append(mv)
                off_all.append(off)
                y, zi = signal.sosfilt(sos, [mv], zi=zi)
                raw_buf.append(mv)
                filt_buf.append(y[0])
                hr_buf.append(y[0])

            if args.record:
                if time.time() - start >= args.record:
                    break
                continue

            now = time.time()
            if raw_buf and now - last_draw > 0.05:            # redraw ~20 times a second
                n = len(raw_buf)
                line_raw.set_data(t[:n], list(raw_buf))
                line_f.set_data(t[:n], list(filt_buf))
                for ax, buf in ((ax_raw, raw_buf), (ax_f, filt_buf)):
                    lo, hi = min(buf), max(buf)
                    pad = max(10, 0.1 * (hi - lo))
                    ax.set_ylim(lo - pad, hi + pad)
                if off_all and off_all[-1]:
                    title.set_text("LEADS OFF: check that all 3 electrodes are stuck on")
                    title.set_color("red")
                else:
                    hr = heart_rate(np.array(hr_buf)) if len(hr_buf) > 3 * FS else None
                    title.set_text(f"ECG   heart rate: {hr:.0f} bpm" if hr else "ECG   (measuring heart rate...)")
                    title.set_color("black")
                last_draw = now
            plt.pause(0.001)
            if not plt.fignum_exists(fig.number):
                break
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()

    if not raw_all:
        raise SystemExit("No data received. Is the ECG sketch uploaded, and the Serial Monitor closed?")
    save(np.array(raw_all), np.array(off_all), sos, time.time() - start)


def save(raw, off, sos, seconds):
    """Write the CSV and a still plot of the last 10 s."""
    stamp = time.strftime("%Y%m%d_%H%M%S")
    np.savetxt(f"ecg_{stamp}.csv", np.column_stack([np.arange(len(raw)) / FS, raw, off]),
               delimiter=",", header="seconds,millivolts,leads_off", comments="", fmt=["%.3f", "%.0f", "%d"])

    filt = signal.sosfiltfilt(sos, raw) if len(raw) > 30 else raw   # zero-phase filter for the still plot
    hr = heart_rate(filt[-8 * FS:])
    print(f"\n{len(raw)} samples in {seconds:.1f} s = {len(raw) / seconds:.0f} samples/s (expect {FS})")
    print(f"Leads off for {100 * off.mean():.1f}% of the time")
    print(f"Heart rate (last 8 s): {hr:.0f} bpm" if hr else "Heart rate: not found (noisy, or leads off)")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    show = min(len(raw), 10 * FS)
    t = np.arange(show) / FS
    fig, (a, b) = plt.subplots(2, 1, sharex=True, figsize=(11, 6))
    a.plot(t, raw[-show:], lw=0.8, color="gray")
    a.set_ylabel("raw ADC (mV)")
    b.plot(t, filt[-show:], lw=1.0, color="crimson")
    b.set_ylabel(f"0.5-40 Hz + {MAINS_HZ} Hz notch (mV)")
    b.set_xlabel("seconds")
    fig.suptitle(f"ECG from AD8232 + ESP32" + (f"   heart rate {hr:.0f} bpm" if hr else ""))
    fig.tight_layout()
    fig.savefig(f"ecg_{stamp}.png", dpi=110)
    print(f"Saved ecg_{stamp}.csv and ecg_{stamp}.png")


if __name__ == "__main__":
    main()
