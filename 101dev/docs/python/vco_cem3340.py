"""
CEM3340 VCO model driven by the external network read from the scan.

What is NOT known from the files we have: the chip's internal ramp current law,
comparator thresholds and tempco. Those are parameters here, marked G19-G21, and
calibrated only to the service manual (A = 442 Hz tune reference, PW 50%..0%).
The external network (R98, R97, R95, R93, R96, R94, C39, C37, C38, VR4, VR5, VR7,
VR6, R108, R105, R106, R101) fixes the scaling through these parameters.
"""
import numpy as np
from scipy.io import wavfile
from sh101_guessed import FS, A4_HZ, RANGE_OCT, envelope, ladder
from vco_pulse import polyblep

# ---- internal parameters (guesses) ----
G19_PW_COMP_OFFSET = 0.0    # datasheet PWM offset: 0 typ (+/-15 mV max); was a guess of 0.02
G20_PW_CURVE = 0.0          # duty nonlinearity: 0 = linear (guess)
G21_TEMPCO = 50e-6        # datasheet oscillator drift: +/-50 ppm typ (200 ppm max)

def freq(note, rng="8", tune=1.0, kcv_gain=1.0):
    """Pitch with 1 V/oct tracking; tune trims the 442 Hz reference by a fraction."""
    return A4_HZ*tune*2**(kcv_gain*(note-69)/12.0)*2**RANGE_OCT[rng]

def duty(wiper, pwm=0.0):
    """Duty from the PW wiper (0..1) plus PWM depth (0..1). Linear, with guessed comparator offset."""
    base = 0.5*wiper + 0.25*pwm
    d = np.clip(base + G19_PW_COMP_OFFSET*(1 - wiper), 0.01, 0.49)
    return d

def square(f, d, n):
    dt = f/FS; ph = np.cumsum(np.full(n, dt)) % 1.0
    y = np.where(ph < d, 1.0, -1.0)
    y += -polyblep(ph, dt) + polyblep((ph-d) % 1.0, dt)
    return y

def sawtooth(f, n):
    dt = f/FS; ph = np.cumsum(np.full(n, dt)) % 1.0
    return 2*ph - 1 - polyblep(ph, dt)

if __name__ == "__main__":
    print("== Calibration (service manual) ==")
    print(f"  A4 at 8', tune = 1.0: {freq(69):.2f} Hz  (target 442.00)")
    print("== Tracking across the keyboard ==")
    for n in [33, 45, 57, 69, 81]:
        err = 1200*np.log2(freq(n)/(A4_HZ*2**((n-69)/12)))
        print(f"  note {n} ({(n-69)/12:+.2f} oct from A4): tracking error {err:+.2f} cents")
    print("== PW wiper vs duty (G17; G19 now 0 per datasheet) ==")
    for w in [1.0, 0.8, 0.5, 0.2, 0.0]:
        print(f"  wiper {w:.1f}: duty {duty(w)*100:5.1f}%")
    print("  note: duty is clamped to 1%..49% for numerical safety; the datasheet allows 0% (PWM 0 V).")
    print("  note: tracking error is zero by construction (same 1 V/oct law used for calibration);")
    print("        it checks the arithmetic, not the chip. The CEM3340 internal law is G20.")

    # Render a preview with this VCO (same bassline, PWM from envelope)
    seq=[(33,0.5),(40,0.5),(45,0.5),(48,0.5),(45,0.5),(40,0.5),(33,0.75)]
    pieces=[]
    for i,(note,dur) in enumerate(seq):
        n=int((dur+0.25)*FS); env=envelope(n,0.005,0.25,0.35,0.25,dur)
        osc = square(freq(note), duty(0.7, pwm=0.0)*np.ones(n) + 0.25*env*0.5, n)
        cut = 1000.0*2**(3.5*env)
        pieces.append(ladder(osc*0.6, cut, min(1.0+0.4*i,3.6))*env)
    a=np.concatenate(pieces); a=a/(np.max(np.abs(a))+1e-9)*0.8
    wavfile.write("sh101_cem_vco.wav", FS, (a*32767).astype(np.int16))
    print(f"wrote sh101_cem_vco.wav ({len(a)/FS:.1f} s)")
