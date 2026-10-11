"""
Cut a time window out of the OpenBCI GUI's raw recordings (OpenBCI-RAW-*.txt) and save it gzip-compressed,
keeping the GUI's own header and columns. Used to publish the exact data behind each test.

Usage:
    python live_inference/extract_recording.py "2026-10-08 01:30:10" "2026-10-08 01:31:05" recordings/11_blinks_dry.txt.gz
    python live_inference/extract_recording.py --test runs/validate_blinks_20261008_013103.json recordings/11_blinks_dry.txt.gz
"""

import argparse
import glob
import gzip
import json
import os
from datetime import datetime

from breathing_hr import FS, RECORDINGS


def window_from_test(path, pad=2):
    m = json.load(open(path))
    if "phases" in m:
        a, b = m["phases"][0]["start"], m["phases"][-1]["end"]
    else:
        a, b = m["start"], m["end"]
    fmt = lambda x: datetime.fromtimestamp(x).strftime("%Y-%m-%d %H:%M:%S")
    return fmt(a - pad), fmt(b + pad)


def extract(a, b, out):
    header, rows = None, []
    for f in sorted(glob.glob(os.path.join(RECORDINGS, "*", "OpenBCI-RAW-*.txt"))):
        name = os.path.basename(f)[12:31]  # file start "YYYY-MM-DD_HH-MM-SS"
        start = name[:10] + " " + name[11:].replace("-", ":")
        if start > b:
            continue
        h, found = [], False
        with open(f) as fh:
            for line in fh:
                if line[0] == "%" or line.startswith("Sample"):
                    h.append(line)
                    continue
                stamp = line.rsplit(",", 1)[-1].strip()[:19]
                if stamp < a:
                    continue
                if stamp > b:
                    break
                rows.append(line)
                found = True
        if found and header is None:
            header = h
    if not rows:
        raise SystemExit(f"No GUI samples between {a} and {b}")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with gzip.open(out, "wt") as g:
        g.writelines(header + rows)
    print(f"Saved {out}: {len(rows) / FS:.1f} s, {os.path.getsize(out) // 1024} KB")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("times", nargs="*", help="START END (YYYY-MM-DD HH:MM:SS), or omit with --test")
    ap.add_argument("--test", help="validate_*.json: use its recorded start/end")
    ap.add_argument("out")
    args = ap.parse_args()
    a, b = window_from_test(args.test) if args.test else args.times[:2]
    extract(a, b, args.out)


if __name__ == "__main__":
    main()
