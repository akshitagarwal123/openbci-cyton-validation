"""Read the ESP32's fake Cyton data with BrainFlow and check it.

Run on the Mac (same Wi-Fi as the ESP32):
    python3 brainflow_fake8.py --ip 192.168.1.12             # 10 s test, prints a report
    python3 brainflow_fake8.py --ip 192.168.1.12 --plot      # also saves brainflow_fake8.png

The ESP32 prints its IP in the Serial Monitor after it joins Wi-Fi.
"""
import argparse    # read --ip, --seconds, --plot
import time        # sleep while data streams in

import numpy as np                                                    # number arrays and FFT
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds   # BrainFlow

# What the ESP32 generates, so we can check BrainFlow got the right thing.
EXPECTED_HZ = [10, 10, 20, 6, 12, 8, 15, 30]
EXPECTED_UV = [20, 15, 10, 25, 12, 18, 8, 5]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", required=True, help="ESP32 IP address (from the Serial Monitor)")
    ap.add_argument("--port", type=int, default=6677, help="TCP port BrainFlow opens on the Mac")
    ap.add_argument("--seconds", type=float, default=10, help="how long to stream")
    ap.add_argument("--plot", action="store_true", help="save a plot to brainflow_fake8.png")
    args = ap.parse_args()

    board_id = BoardIds.CYTON_WIFI_BOARD                        # "Cyton + Wi-Fi Shield"
    params = BrainFlowInputParams()
    params.ip_address = args.ip                                 # where the (fake) Wi-Fi Shield is
    params.ip_port = args.port                                  # BrainFlow listens here for the data
    params.timeout = 15                                         # seconds to wait for HTTP replies

    BoardShim.enable_dev_board_logger()                         # show BrainFlow's own log lines
    board = BoardShim(board_id, params)
    fs = BoardShim.get_sampling_rate(board_id)                  # 1000 Hz for Cyton Wi-Fi
    eeg = BoardShim.get_eeg_channels(board_id)                  # rows that hold ch1..ch8
    pkg = BoardShim.get_package_num_channel(board_id)           # row that holds the 0..255 counter

    print(f"Connecting to fake Cyton at {args.ip} ...")
    board.prepare_session()                                     # /board, /tcp, "~4", "d"
    board.start_stream()                                        # /stream/start
    print(f"Streaming for {args.seconds:.0f} s ...")
    time.sleep(args.seconds)
    data = board.get_board_data()                               # everything received so far
    board.stop_stream()                                         # /stream/stop
    board.release_session()

    # --- report ---
    n = data.shape[1]                                           # number of samples received
    print(f"\nReceived {n} samples in {args.seconds:.0f} s = {n / args.seconds:.0f} samples/s "
          f"(BrainFlow expects {fs})")

    # Lost samples: the packet counter goes 0,1,2..255,0,1.. so any jump other than +1 is a gap.
    steps = np.diff(data[pkg]) % 256
    lost = int(np.sum(steps[steps != 1] - 1))
    print(f"Lost samples (gaps in the 0..255 counter): {lost} ({100 * lost / (n + lost):.2f}%)")

    # Each channel's main frequency (FFT peak) and amplitude, vs what the ESP32 makes.
    print("\nch  expect Hz  got Hz   expect uV  got uV")
    for i, row in enumerate(eeg):
        x = data[row] - np.mean(data[row])                      # remove any DC offset
        spec = np.abs(np.fft.rfft(x))                           # strength at each frequency
        freqs = np.fft.rfftfreq(len(x), 1 / fs)                 # which frequency each bin is
        peak = freqs[np.argmax(spec[1:]) + 1]                   # strongest frequency (skip 0 Hz)
        amp = np.sqrt(2) * np.std(x)                            # sine amplitude from its spread
        print(f"{i + 1:2d}  {EXPECTED_HZ[i]:9.0f}  {peak:6.1f}   {EXPECTED_UV[i]:9.0f}  {amp:6.1f}")

    if args.plot:
        import matplotlib
        matplotlib.use("Agg")                                   # draw to a file, no window
        import matplotlib.pyplot as plt
        show = int(min(n, 2 * fs))                              # plot the last 2 s
        t = np.arange(show) / fs
        fig, axes = plt.subplots(len(eeg), 1, sharex=True, figsize=(10, 9))
        for i, row in enumerate(eeg):
            axes[i].plot(t, data[row][-show:], lw=0.7)
            axes[i].set_ylabel(f"ch{i + 1}\nuV", rotation=0, labelpad=18, fontsize=8)
        axes[-1].set_xlabel("seconds")
        fig.suptitle("Fake 8-channel data received by BrainFlow (CYTON_WIFI)")
        fig.tight_layout()
        fig.savefig("brainflow_fake8.png", dpi=110)
        print("\nSaved brainflow_fake8.png")


if __name__ == "__main__":
    main()
