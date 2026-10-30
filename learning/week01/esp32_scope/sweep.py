# Sweeps the esp32_scope sketch over several frequencies and compares the RC filter with theory.
# Usage: python sweep.py   (edit R and C below; close the Arduino Serial Monitor first)
import serial, time, math, cmath, numpy as np
R, C = 1e3, 47e-6; fc = 1/(2*math.pi*R*C)
s = serial.Serial(); s.port='/dev/cu.usbserial-A5069RR4'; s.baudrate=115200; s.timeout=2; s.dtr=False; s.rts=False; s.open(); time.sleep(2); s.reset_input_buffer()
def lines_for(f, count):
    out, tries = [], 0
    while len(out) < count:
        tries += 1
        if tries > 800: raise SystemExit(f"no data at {f} Hz")
        l = s.readline().decode(errors='ignore').strip()
        try:
            d = dict(p.split(':') for p in l.split(','))
            if abs(float(d['freq_Hz_div1000'])*1000 - f) < 0.01:
                out.append((float(d['input_V']), float(d['output_V'])))
        except Exception: pass
    return out
print(f"R = 1 kΩ, C = 47 µF, cutoff f_c = {fc:.1f} Hz   (amplitudes are peak-to-peak)\n")
print(" freq |  input | across C (out) | across R        | out % meas/theory | R % meas/theory | out delay")
for f in [2, 3.4, 5, 10, 20, 50, 100]:
    if f < 5: continue
    s.write(f"{f}\n".encode()); s.reset_input_buffer()
    time.sleep(1.5); s.reset_input_buffer(); lines_for(f, 60)
    d = np.array(lines_for(f, 50))
    cyc = max(2, math.ceil(50*f/10000)); th = 2*math.pi*cyc*np.arange(50)/50
    A = np.c_[np.sin(th), np.cos(th), np.ones(50)]
    def ph(y): a, b, _ = np.linalg.lstsq(A, y, rcond=None)[0]; return complex(a, b)
    vi, vo = ph(d[:,0]), ph(d[:,1]); vr = vi - vo
    x = f/fc; go, gr = 1/math.sqrt(1+x*x), x/math.sqrt(1+x*x)
    dly = math.degrees(cmath.phase(vo/vi))
    print(f"{f:5} | {2*abs(vi):4.2f} V | {2*abs(vo):6.2f} V       | {2*abs(vr):5.2f} V         |   {abs(vo/vi)*100:3.0f} % / {go*100:3.0f} %     |  {abs(vr/vi)*100:3.0f} % / {gr*100:3.0f} %   | {dly:5.0f}° (theory {-math.degrees(math.atan(x)):.0f}°)")
s.write(b"5\n"); s.readline()
