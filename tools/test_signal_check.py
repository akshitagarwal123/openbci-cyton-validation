"""
Check the Cyton's internal ADS1299 test signal on all 8 channels (BrainFlow direct).

The GUI's "Test" input type only routes channels to the test input; the generator
itself is switched on by the board commands below, which the GUI v6 cannot send.
Close the OpenBCI GUI first (one program per serial port).

    '-'  1x amplitude, slow  (±1875 µV, period 1.024 s)
    '='  1x amplitude, fast  (±1875 µV, period 0.512 s)
    'd'  restore default channel settings afterwards

Usage:
    python live_inference/test_signal_check.py [--port /dev/cu.usbserial-XXXX]
"""

import argparse
import json
import os
import time
from datetime import datetime

import numpy as np
from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams

from breathing_hr import OUT_DIR
from validate_board import TESTSIG_HALF_AMPS, TESTSIG_PERIODS, analyse_square

BOARD = BoardIds.CYTON_BOARD.value
MODES = [("-", "1x slow", TESTSIG_HALF_AMPS["1x"], TESTSIG_PERIODS["slow"]),
         ("=", "1x fast", TESTSIG_HALF_AMPS["1x"], TESTSIG_PERIODS["fast"])]


def record(board, seconds):
    board.get_board_data()                     # discard anything buffered
    time.sleep(seconds)
    return board.get_board_data()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/cu.usbserial-DP04WGKF")
    ap.add_argument("--seconds", type=float, default=12)
    args = ap.parse_args()

    params = BrainFlowInputParams()
    params.serial_port = args.port
    BoardShim.disable_board_logger()
    board = BoardShim(BOARD, params)
    eeg = BoardShim.get_eeg_channels(BOARD)
    fs = BoardShim.get_sampling_rate(BOARD)
    board.prepare_session()
    results, ok_all = {}, True
    try:
        board.start_stream()
        for cmd, name, half_ref, per_ref in MODES:
            board.config_board(cmd)
            time.sleep(2)                      # let the signal settle
            data = record(board, args.seconds)
            print(f"\n{name} (command '{cmd}'): expect ±{half_ref:.0f} µV, period {per_ref:.3f} s")
            halves = []
            for i, row in enumerate(eeg):
                x = data[row][fs:]             # drop the first second
                half, period = analyse_square(x)
                a_err = 100 * (half - half_ref) / half_ref
                p_err = 100 * (period - per_ref) / per_ref
                ok = abs(a_err) <= 2 and abs(p_err) <= 2
                ok_all &= ok
                halves.append(half)
                results[f"{name} ch{i + 1}"] = {"half_amp_uv": round(float(half), 1), "period_s": round(period, 4),
                                                 "amp_err_pct": round(a_err, 2), "period_err_pct": round(p_err, 2),
                                                 "pass": bool(ok)}
                print(f"  ch{i + 1}: ±{half:8.1f} µV ({a_err:+5.2f} %)   period {period:.4f} s ({p_err:+5.2f} %)  "
                      f"{'PASS' if ok else 'FAIL'}")
            spread = 100 * (max(halves) - min(halves)) / np.mean(halves)
            gain_ok = spread <= 0.5
            ok_all &= gain_ok
            results[f"{name} gain spread"] = {"spread_pct": round(float(spread), 3), "pass": bool(gain_ok)}
            print(f"  gain match across 8 channels: spread {spread:.3f} %  {'PASS' if gain_ok else 'FAIL'} (≤ 0.5 %)")
    finally:
        board.config_board("d")                # back to default channel settings
        board.stop_stream()
        board.release_session()

    print(f"\nTEST SIGNAL — {'PASS ✅' if ok_all else 'FAIL ❌'}")
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"validate_testsignal_{datetime.now():%Y%m%d_%H%M%S}_result.json")
    with open(out, "w") as fh:
        json.dump({"test": "testsignal", "time": datetime.now().isoformat(timespec="seconds"),
                   "passed": bool(ok_all), "results": results}, fh, indent=2)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
