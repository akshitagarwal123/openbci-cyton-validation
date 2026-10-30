"""Capture input, output and the voltage across R at one frequency from esp32_scope and plot them.
Usage: python rc_waves_plot.py --freq 100   (close the Arduino Serial Monitor/Plotter first)"""
import argparse, time, math, serial, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
ap = argparse.ArgumentParser(); ap.add_argument("--freq", type=float, default=100)
ap.add_argument("--port", default="/dev/cu.usbserial-A5069RR4"); a = ap.parse_args(); f = a.freq
s = serial.Serial(); s.port, s.baudrate, s.timeout = a.port, 115200, 3; s.dtr = s.rts = False; s.open()
time.sleep(1.5); s.write(f"{f}\n".encode()); time.sleep(1.5); s.reset_input_buffer()
def frame():
    out = []
    while len(out) < 50:
        l = s.readline().decode(errors="ignore").strip()
        try:
            d = dict(p.split(":") for p in l.split(","))
            if abs(float(d["freq_Hz_div1000"]) * 1000 - f) < 0.01: out.append((float(d["input_V"]), float(d["output_V"])))
        except Exception: pass
    return np.array(out)
frame(); frames = [frame() for _ in range(4)]
cyc = max(2, math.ceil(50 * f / 10000)); th = 2 * math.pi * cyc * np.arange(50) / 50
A = np.c_[np.sin(th), np.cos(th), np.ones(50)]
def fit(y): a, b, c = np.linalg.lstsq(A, y, rcond=None)[0]; return complex(a, b), c
# align frames by input phase, then average to reduce ADC noise
ref, _ = fit(frames[0][:, 0]); acc = []
for fr in frames:
    p, _ = fit(fr[:, 0]); shift = round((np.angle(p) - np.angle(ref)) / (2 * math.pi / 50 * cyc)) % 50
    acc.append(np.roll(fr, shift, axis=0))
d = np.mean(acc, axis=0); vin, vout = d[:, 0], d[:, 1]; vr = vin - vout
t = np.arange(50) * (cyc / f) / 50 * 1000
pi_, ci = fit(vin); po, co = fit(vout); pr, cr = fit(vr)
def desc(name, p, c): pk = abs(p); return f"{name}: DC {c:.2f} V, peak {pk:.2f} V, p-p {2*pk:.2f} V, RMS {pk/math.sqrt(2):.2f} V"
print(f"input max {vin.max():.2f} V min {vin.min():.2f} V | across R max {vr.max():+.2f} V min {vr.min():+.2f} V avg {vr.mean():+.2f} V rms {np.sqrt(np.mean(vr**2)):.2f} V")
for line in (desc("input (G35)", pi_, ci), desc("across C (output, G34)", po, co), desc("across R (input-output)", pr, cr)): print(line)
fig, ax = plt.subplots(2, 1, figsize=(9, 6.5), sharex=True)
ax[0].plot(t, vin, "o-", ms=3, color="#c27a1a", label=f"input (G35)  DC {ci:.2f} V, peak {abs(pi_):.2f} V")
ax[0].plot(t, vout, "o-", ms=3, color="#0b7a8a", label=f"output = across C (G34)  DC {co:.2f} V, peak {abs(po):.2f} V")
ax[0].set_ylabel("volts to GND"); ax[0].legend(loc="lower right", fontsize=9); ax[0].grid(alpha=.3)
ax[0].set_title(f"{f:g} Hz into 1 kΩ + 47 µF: where the voltage goes")
ax[1].plot(t, vr, "o-", ms=3, color="#b33a2e", label=f"across R  max {vr.max():+.2f} V, min {vr.min():+.2f} V, RMS {np.sqrt(np.mean(vr**2)):.2f} V, average {vr.mean():+.2f} V")
ax[1].axhline(0, color="gray", lw=1); ax[1].set_ylabel("volts across R"); ax[1].set_xlabel("time (ms)")
ax[1].legend(loc="lower right", fontsize=9); ax[1].grid(alpha=.3)
ax[1].text(0.01, 0.92, "A DC meter shows only the average of this wave (the line it wobbles around)", transform=ax[1].transAxes, fontsize=9, color="gray")
plt.tight_layout(); plt.savefig(f"rc_waves_{f:g}Hz.png", dpi=130); print(f"saved rc_waves_{f:g}Hz.png")
