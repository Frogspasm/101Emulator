"""
Guess-based SH-101 voice model. Every number marked (Gxx) comes from guess_ledger.md
or a new guess added here (G12-G15). Nothing here is confirmed by a photo or unit.

Chain: KCV (1 V/oct) -> VCO (CEM3340, tune calibrated to A4 = 442 Hz) -> VCF (4-pole,
pin 9 volts/octave from the summer) -> VCA -> output.
"""
import numpy as np
from scipy.io import wavfile

FS = 44100

# ---------------- VCO (guessed calibration) ----------------
A4_HZ = 442.0            # service manual tune reference (A = 442 Hz)
RANGE_OCT = {"16": -1, "8": 0, "4": 1, "2": 2}   # octaves relative to 8 ft (A4 = 442 Hz at 8 ft, G12)

def vco_hz(midi_note, rng="8"):
    return A4_HZ * 2 ** ((midi_note - 69) / 12) * 2 ** RANGE_OCT[rng]

# ---------------- Cutoff (guessed summer) ----------------
PIN9_PER_BUS = 0.1110     # divider ratio, TH1 = 1k NTC (G6)
VC_OCT = 0.019            # datasheet sensitivity, V per octave at pin 9 (magnitude)
FC0 = 250.0               # single-stage pole at VC = 0
K4 = 0.435                # four-pole -3 dB / single-stage pole (G11)
KYB_GAIN = VC_OCT / PIN9_PER_BUS  # exact: one volt of KCV must move pin 9 by one octave's worth (19 mV); gives 0.1712 (G13)

def pin9_to_cutoff_hz(v9):
    # v9 is pin 9 relative to pin 1; negative v9 raises cutoff (datasheet sign)
    return K4 * FC0 * 2 ** (-v9 / VC_OCT)

def bus_for_cutoff(target_hz):
    """Bus offset (beyond the keyboard term) that puts the 4-pole -3 dB point at target_hz."""
    v9 = -np.log2(target_hz / (K4 * FC0)) * VC_OCT
    return v9 / PIN9_PER_BUS

# Cutoff slider (VR17, FREQ): spec 10 Hz to 20 kHz (service manual). Bus offset at each end,
# computed from the datasheet sensitivity and the 0.111 divider (G14, now closed by the spec):
#   CUT_BUS_MIN = bus offset giving 10 Hz (slider bottom); CUT_BUS_MAX = bus offset giving 20 kHz (top).
# Span is 1.877 V, about 11 octaves. Slider position is linear in volts, so linear in octaves.
CUT_BUS_MIN, CUT_BUS_MAX = +0.589, -1.288

def cutoff_slider_position(target_hz, kcv_at_note):
    need = bus_for_cutoff(target_hz) - KYB_GAIN * kcv_at_note
    return (need - CUT_BUS_MIN) / (CUT_BUS_MAX - CUT_BUS_MIN)  # 0..1 travel

# ---------------- DSP (same building blocks as the preview) ----------------
def polyblep(t, dt):
    t = t % 1.0; out = np.zeros_like(t)
    m = t < dt; x = t[m] / dt; out[m] = 2*x - x*x - 1.0
    m2 = t > 1 - dt; x = (t[m2] - 1) / dt; out[m2] = x*x + 2*x + 1.0
    return out

def saw(freq, n):
    ph = np.cumsum(np.full(n, freq / FS)) % 1.0
    return 2*ph - 1 - polyblep(ph, freq / FS)

def ladder(x, cut_hz, res):
    y1 = y2 = y3 = y4 = 0.0; out = np.zeros_like(x)
    g = 1 - np.exp(-2*np.pi*np.clip(cut_hz, 20, FS*0.45)/FS)
    for i in range(len(x)):
        u = np.tanh(x[i] - res*y4)
        y1 += g[i]*(u - y1); y2 += g[i]*(np.tanh(y1) - y2)
        y3 += g[i]*(np.tanh(y2) - y3); y4 += g[i]*(np.tanh(y3) - y4)
        out[i] = y4
    return out

def envelope(n, a, d, s, r, dur):
    t = np.arange(n)/FS; e = np.zeros(n)
    m = t < a; e[m] = t[m]/a
    m = (t >= a) & (t < a+d); e[m] = 1 - (1-s)*(t[m]-a)/d
    m = (t >= a+d) & (t < dur); e[m] = s
    m = t >= dur; e[m] = s*np.maximum(0, 1-(t[m]-dur)/r)
    return e

# ---------------- Voice ----------------
def voice(note, dur, cut_panel_hz, env_amt_oct, res, rel=0.25):
    n = int((dur+rel)*FS); f = vco_hz(note)
    osc = saw(f, n)
    env = envelope(n, 0.005, 0.25, 0.35, rel, dur)
    # keyboard tracking: KCV in volts relative to C4 (1 V/oct), scaled into the bus by KYB_GAIN
    kcv = (note - 60)/12.0
    base = cut_panel_hz * 2 ** (KYB_GAIN*kcv / (VC_OCT/PIN9_PER_BUS))
    cut = base * 2 ** (env_amt_oct*env)
    return ladder(osc*0.6, cut, res) * env

if __name__ == "__main__":
    print("== VCO ==")
    for n, lab in [(69, "A4"), (45, "A2"), (33, "A1")]:
        print(f"  {lab}: 8' = {vco_hz(n):.2f} Hz, 16' = {vco_hz(n,'16'):.2f} Hz")
    print("\n== Cutoff slider needed for 1 kHz at A4 (C4 = KCV 0) ==")
    kcv_a4 = (69-60)/12
    print(f"  bus target offset: {bus_for_cutoff(1000):.3f} V (before keyboard term)")
    print(f"  keyboard term at A4: {KYB_GAIN*kcv_a4:.3f} V")
    print(f"  slider travel needed: {cutoff_slider_position(1000, kcv_a4):.3f} (0 = bottom, 1 = top; G14)")
    print("\n== Tracking check: cutoff shift per octave at fixed slider ==")
    f1 = pin9_to_cutoff_hz(PIN9_PER_BUS*(KYB_GAIN*1.0))
    print(f"  one octave of KCV moves pin 9 by {PIN9_PER_BUS*KYB_GAIN*1000:.1f} mV -> "
          f"{'ok' if abs(PIN9_PER_BUS*KYB_GAIN*1000 - 19) < 0.5 else 'off'} vs datasheet 19 mV/oct")
    print("\n== Resonance: threshold from component model ==")
    try:
        import sh101_vcf as m
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo+hi)/2; p = m.poles(m.GM0, mid); p = p[np.abs(p.imag) > 2*np.pi*50]
            (hi := mid) if p.real.max() > 0 else (lo := mid)
        print(f"  self-oscillation at VR18 = {hi:.3f}")
    except Exception as e:
        print("  (component model unavailable)", e)

    # preview v2: same bassline, now with the guessed panel->cutoff mapping
    seq = [(33,0.5),(40,0.5),(45,0.5),(48,0.5),(45,0.5),(40,0.5),(33,0.75)]
    pieces = [voice(n, d, cut_panel_hz=1000.0, env_amt_oct=3.5, res=min(1.0+0.4*i,3.6))
              for i,(n,d) in enumerate(seq)]
    audio = np.concatenate(pieces); audio = audio/(np.max(np.abs(audio))+1e-9)*0.8
    wavfile.write("sh101_guessed.wav", FS, (audio*32767).astype(np.int16))
    print(f"\nwrote sh101_guessed.wav ({len(audio)/FS:.1f} s), cutoff panel = 1 kHz at C4")
