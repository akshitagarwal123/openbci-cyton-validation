"""Frequency content of blinks and jaw clenches vs rest, from saved validate_board runs."""
import json, sys
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import welch, iirnotch, filtfilt
from breathing_hr import FS, load_recordings

BANDS = [("0.5–4 Hz (eye/slow)", 0.5, 4), ("4–8 theta", 4, 8), ("8–13 alpha", 8, 13), ("13–30 beta", 13, 30),
         ("30–45 gamma/muscle", 30, 45), ("55–100 high (muscle)", 55, 100)]


def segs(t, x, wins):
    return [x[(t >= a) & (t < b)] for a, b in wins if np.sum((t >= a) & (t < b)) >= FS // 2]


def spectrum(pieces, nper):
    ps = []
    for s in pieces:
        s = s - s.mean()
        f, p = welch(s, FS, nperseg=min(nper, len(s)), nfft=FS)
        ps.append(p)
    return f, np.median(ps, axis=0)


def band(f, p, lo, hi):
    return float(np.sqrt(p[(f >= lo) & (f < hi)].sum() * (f[1] - f[0])))


def analyse(meta_path, ev_off, ev_len, name):
    m = json.load(open(meta_path))
    d = load_recordings(m["start"], m["end"])
    t, x = d["t"].values, d["EXG Channel 0"].values.astype(float)
    for f0 in (50, 100):
        b, a = iirnotch(f0, 30, FS); x = filtfilt(b, a, x)
    cues = m["cues"]
    ev = [(c + ev_off, c + ev_off + ev_len) for c in cues]
    rest = []
    edges = [m["start"] + 1] + [c for c in cues] + [m["end"]]
    for i, c in enumerate(cues + [m["end"]]):
        lo = (cues[i - 1] + ev_off + ev_len + 0.5) if i else m["start"] + 3
        hi = c + 0.8
        while lo + ev_len <= hi:
            rest.append((lo, lo + ev_len)); lo += ev_len
    f, pe = spectrum(segs(t, x, ev), FS)
    _, pr = spectrum(segs(t, x, rest), FS)
    rows = [(n, band(f, pe, lo, hi), band(f, pr, lo, hi)) for n, lo, hi in BANDS]
    return name, f, pe, pr, rows, len(ev), len(rest)


res = [analyse("runs/validate_blinks_20261008_013103.json", 1.5, 0.8, "Blink"),
       analyse("runs/validate_jaw_20261008_212352.json", 1.5, 2.0, "Jaw clench")]
out = {}
fig, axs = plt.subplots(1, 2, figsize=(13, 4.4))
for ax, (name, f, pe, pr, rows, ne, nr) in zip(axs, res):
    m = (f >= 0.5) & (f <= 100)
    ax.semilogy(f[m], np.sqrt(pr[m]), color="#898781", lw=1.6, label=f"rest ({nr} windows)")
    ax.semilogy(f[m], np.sqrt(pe[m]), color="#eb6834" if name == "Jaw clench" else "#2a78d6", lw=1.8, label=f"{name.lower()} ({ne} events)")
    ax.axvspan(48, 52, color="#ecebe8"); ax.text(50, ax.get_ylim()[1] if False else 0, "")
    ax.set(title=f"{name} vs rest, channel 1 (dry, forehead)", xlabel="frequency (Hz)", ylabel="amplitude (µV/√Hz)")
    ax.legend(frameon=False); ax.spines[["top", "right"]].set_visible(False); ax.grid(axis="y", color="#ecebe8")
    print(f"\n{name}")
    out[name] = []
    for n, e, r in rows:
        print(f"  {n:24s} event {e:7.1f} µV   rest {r:6.1f} µV   ×{e / max(r, 1e-9):5.1f}")
        out[name].append(dict(band=n, event_uv=round(e, 1), rest_uv=round(r, 1), ratio=round(e / max(r, 1e-9), 1)))
fig.suptitle("Which frequencies change during a blink and a jaw clench (50 Hz mains notched out)", x=0.01, ha="left")
plt.tight_layout(); plt.savefig("runs/event_spectra_oct8.png", dpi=110)
json.dump(out, open("runs/event_spectra_oct8.json", "w"), indent=1)
