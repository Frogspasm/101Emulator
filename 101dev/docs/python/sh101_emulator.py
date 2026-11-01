"""
SH-101-style monophonic emulator, built from the models in this folder.

Signal path: keyboard (1 V/oct) -> VCO (saw, pulse with PWM, 1-octave square sub, noise)
-> 4-pole ladder VCF (tanh stages, resonance feedback, keyboard + envelope cutoff tracking)
-> VCA (ENV or GATE) -> output. LFO triangle for vibrato and cutoff.

Values come from the service manual, the scan, and the two datasheets where stated.
Everything marked G36+ is a guess listed in EMULATOR_GUESSES.md.
"""
import numpy as np
from scipy.io import wavfile
from sh101_guessed import ladder, A4_HZ, RANGE_OCT, CUT_BUS_MIN, CUT_BUS_MAX
from keyboard_vca import cutoff_hz

FS = 44100
rng = np.random.default_rng(101)

# ---------- envelope (spec ranges: A 1.5 ms..4 s, D 2 ms..10 s, S 0..100 %, R 2 ms..10 s) ----------
def log_map(pos, lo, hi):           # G36: panel position 0..1 maps exponentially across spec range
    return lo * (hi / lo) ** pos

def adsr(n, dur, a, d, s, r):       # G37: linear attack, exponential decay and release (tau = time/3)
    t = np.arange(n) / FS
    def held(tt):
        return np.where(tt < a, tt / a, s + (1 - s) * np.exp(-(tt - a) / max(d / 3, 1e-4)))
    env = np.zeros(n)
    on = t < dur
    env[on] = held(t[on])
    level = float(held(np.array([dur]))[0]) if dur > 0 else 0.0
    off = ~on
    env[off] = level * np.exp(-(t[off] - dur) / max(r / 3, 1e-4))
    return env

# ---------- oscillator (PolyBLEP, elementwise dt) ----------
def polyblep(t, dt):
    out = np.zeros_like(t)
    m = t < dt; x = t[m] / dt[m]; out[m] = 2 * x - x * x - 1
    m2 = t > 1 - dt; x = (t[m2] - 1) / dt[m2]; out[m2] = x * x + 2 * x + 1
    return out

def vco(freq, duty, n):
    """freq, duty: per-sample arrays. Returns mixed raw VCO components."""
    dt = freq / FS
    ph = np.cumsum(dt) % 1.0
    saw = 2 * ph - 1 - polyblep(ph, dt)
    pulse = np.where(ph < duty, 1.0, -1.0) - polyblep(ph, dt) + polyblep((ph - duty) % 1.0, dt)
    ph2 = np.cumsum(dt / 2) % 1.0                       # G42: sub = square one octave down
    sub = np.where(ph2 < 0.5, 1.0, -1.0) - polyblep(ph2, dt / 2) + polyblep((ph2 - 0.5) % 1.0, dt / 2)
    noise = rng.uniform(-1, 1, n)
    return saw, pulse, sub, noise

# G39: mixer levels follow the scan's summing resistors (level proportional to 1/R, saw = 1)
# G38: noise scaled to 0.3 relative to saw (the source itself is not measured)
MIX = dict(saw=1.0, pulse=0.69, sub=0.57, noise=0.3)

def note_hz(midi, rng_key="8"):
    return A4_HZ * 2 ** ((midi - 69) / 12) * 2 ** RANGE_OCT[rng_key]

def voice(midi, dur, p):
    """Render one note with patch parameters p. Returns mono float array."""
    rel = p["release"]
    n = int((dur + rel) * FS)
    t = np.arange(n) / FS
    lfo = 2 * np.abs(2 * ((p["lfo_rate"] * t) % 1.0) - 1) - 1          # G43: triangle LFO
    f = note_hz(midi, p["range"]) * 2 ** (p["vib_oct"] * lfo)
    env_pw = adsr(n, dur, p["attack_pwm"], p["decay_pwm"], 0.0, rel)     # PWM envelope
    duty = np.clip(0.5 * p["pw"] + p["pwm_amt"] * env_pw, 0.02, 0.98)    # G18: PWM depth 0.25
    saw, pulse, sub, noise = vco(f, duty, n)
    src = (p["w_saw"] * MIX["saw"] * saw + p["w_pulse"] * MIX["pulse"] * pulse
           + p["w_sub"] * MIX["sub"] * sub + p["w_noise"] * MIX["noise"] * noise)
    env = adsr(n, dur, p["attack"], p["decay"], p["sustain"], rel)
    # cutoff: keyboard tracking (1 oct/oct, calibrated) + panel slider + envelope + LFO
    bus = CUT_BUS_MIN + p["cutoff"] * (CUT_BUS_MAX - CUT_BUS_MIN)
    base = cutoff_hz(midi, bus)
    cut = base * 2 ** (p["env_amt"] * 4.0 * env + p["lfo_cut"] * lfo)   # G40: ENV amount max 4 oct
    k = min(4.2 * p["res"] / 0.785, 5.0)                                # G41: self-osc at res ~0.785
    filt = ladder(src * 0.5, cut, k)
    gate = env if p["vca_mode"] == "ENV" else (t < dur).astype(float)
    return filt * gate * p["volume"]                                    # G44: linear VCA

# ---------- patches ----------
BASE = dict(range="8", release=0.2, attack=0.005, decay=0.25, sustain=0.35,
            attack_pwm=0.01, decay_pwm=0.2, pw=0.5, pwm_amt=0.25,
            w_saw=1.0, w_pulse=0.0, w_sub=0.0, w_noise=0.0,
            cutoff=0.3, res=0.4, env_amt=0.6, lfo_rate=5.0, vib_oct=0.0, lfo_cut=0.0,
            vca_mode="ENV", volume=0.8)

def render(seq, p):
    total = max(s + d + p["release"] for _, s, d in seq)
    out = np.zeros(int(total * FS) + 1)
    for midi, start, dur in seq:
        v = voice(midi, dur, p)
        i = int(start * FS)
        out[i:i + len(v)] += v[:max(0, len(out) - i)]
    return out

def norm(x, peak=0.8):
    return x / (np.max(np.abs(x)) + 1e-12) * peak

if __name__ == "__main__":
    # ---- sanity checks ----
    print("== Checks ==")
    print(f"A4 at 8 ft: {note_hz(69):.2f} Hz (service manual 442)")
    print(f"Attack range: {log_map(0,1.5e-3,4):.4f} s .. {log_map(1,1.5e-3,4):.2f} s (spec 1.5 ms .. 4 s)")
    print(f"Decay range:  {log_map(0,2e-3,10):.4f} s .. {log_map(1,2e-3,10):.2f} s (spec 2 ms .. 10 s)")
    f1 = cutoff_hz(60, CUT_BUS_MIN + 0.3*(CUT_BUS_MAX-CUT_BUS_MIN))
    f2 = cutoff_hz(72, CUT_BUS_MIN + 0.3*(CUT_BUS_MAX-CUT_BUS_MIN))
    print(f"Cutoff tracking C4 -> C5: {f1:.1f} -> {f2:.1f} Hz (ratio {f2/f1:.3f}, must be 2.000)")

    # ---- demo: three patches in sequence ----
    bass = dict(BASE, cutoff=0.71, res=0.45, env_amt=0.7, w_saw=1.0, w_sub=0.4, decay=0.3, sustain=0.2)
    pwm = dict(BASE, w_saw=0.0, w_pulse=1.0, pw=0.4, pwm_amt=0.35, cutoff=0.55, res=0.35,
               env_amt=0.3, lfo_rate=5.5, vib_oct=0.01, attack=0.2, decay=0.6, sustain=0.6, release=0.4, vca_mode="ENV")
    whistle = dict(BASE, w_saw=0.0, w_noise=0.0, w_pulse=0.0, w_sub=0.0,
                   cutoff=0.61, res=0.9, env_amt=0.0, lfo_cut=0.08, lfo_rate=4.0,
                   attack=0.02, decay=0.4, sustain=0.6, release=0.3, vca_mode="GATE")
    whistle["w_saw"] = 0.05  # faint source so the ladder has something to ring on

    seq_bass = [(33,0.0,0.45),(40,0.5,0.45),(45,1.0,0.45),(48,1.5,0.45),(45,2.0,0.45),(40,2.5,0.45),(33,3.0,0.7)]
    seq_pwm = [(57,0.0,0.9),(60,1.0,0.9),(64,2.0,0.9),(69,3.0,1.2)]
    seq_whistle = [(60,0.0,0.6),(67,0.8,0.6),(72,1.6,0.9)]

    a = render(seq_bass, bass)
    b = render(seq_pwm, pwm)
    c = render(seq_whistle, whistle)
    audio = np.concatenate([a, np.zeros(int(0.4*FS)), b, np.zeros(int(0.4*FS)), c])
    wavfile.write("sh101_emulator_demo.wav", FS, (norm(audio)*32767).astype(np.int16))
    print(f"wrote sh101_emulator_demo.wav ({len(audio)/FS:.1f} s): bass / PWM lead / resonant whistle")
