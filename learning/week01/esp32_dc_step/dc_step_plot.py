"""Run the DC step on the ESP32 and plot the capacitor charging vs theory.
Usage: python dc_step_plot.py [--r 1000] [--c 47e-6]   (close the Arduino Serial Monitor first)"""
import argparse, time, math, serial, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
ap = argparse.ArgumentParser(); ap.add_argument("--r", type=float, default=1e3); ap.add_argument("--c", type=float, default=47e-6)
ap.add_argument("--port", default="/dev/cu.usbserial-A5069RR4"); a = ap.parse_args()
s = serial.Serial(); s.port, s.baudrate, s.timeout = a.port, 115200, 3; s.dtr = s.rts = False; s.open()
time.sleep(1); s.reset_input_buffer(); s.write(b"s\n")
rows, started = [], False
while True:
    l = s.readline().decode(errors="ignore").strip()
    if not l: raise SystemExit("no data from ESP32")
    if l.startswith("t_ms"): started = True; continue
    if l == "done" and started: break
    if started: rows.append([float(x) for x in l.split(",")])
d = np.array(rows); t, vi, vo = d[:, 0], d[:, 1], d[:, 2]
tau = a.r * a.c * 1000; final = vi[-20:].mean()
theory = final * (1 - np.exp(-t / tau))
i63 = np.argmax(vo >= 0.632 * vo[-20:].mean())
print(f"RC = {tau:.0f} ms   final input {final:.2f} V   output reached 63% at {t[i63]:.1f} ms")
for ms in [0, 25, 47, 100, 150, 250]:
    k = np.argmin(abs(t - ms)); print(f"  t={ms:3d} ms  input {vi[k]:.2f} V  output {vo[k]:.2f} V  across R {vi[k]-vo[k]:.2f} V  theory out {theory[k]:.2f} V")
plt.figure(figsize=(8, 4.5))
plt.plot(t, vi, label="input (G35)", color="#c27a1a"); plt.plot(t, vo, label="output across C (G34)", color="#0b7a8a", lw=2)
plt.plot(t, theory, "--", color="gray", label=f"theory 1−e^(−t/RC), RC = {tau:.0f} ms")
plt.axvline(tau, color="gray", ls=":"); plt.text(tau + 3, 0.1, "1 RC", color="gray")
plt.xlabel("time after DC switched on (ms)"); plt.ylabel("volts"); plt.title("DC step into the RC filter: capacitor charging")
plt.grid(alpha=.3); plt.legend(); plt.tight_layout(); plt.savefig("dc_step.png", dpi=130); print("saved dc_step.png")
