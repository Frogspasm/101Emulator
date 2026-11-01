"""
Streaming (block-based) SH-101 emulator voice. Same models as sh101_emulator.py,
but state is kept between blocks so it can run live from a MIDI keyboard.
Monophonic, last-note priority. Guesses are listed in EMULATOR_GUESSES.md (G36-G44).
"""
import numpy as np
from sh101_guessed import A4_HZ, RANGE_OCT, CUT_BUS_MIN, CUT_BUS_MAX, VC_OCT
from keyboard_vca import cutoff_hz

try:                                    # optional speed-up: pip install numba
    from numba import njit
    HAVE_NUMBA = True
except ImportError:
    def njit(*a, **k):
        def deco(f):
            return f
        return deco
    HAVE_NUMBA = False

FS = 44100
BLOCK = 512                             # larger block = fewer dropouts, slightly more delay

def note_hz(midi, rng_key="8"):
    return A4_HZ * 2 ** ((midi - 69) / 12) * 2 ** RANGE_OCT[rng_key]

def log_map(pos, lo, hi):                       # G36
    return lo * (hi / lo) ** pos

STAGE = {"idle": 0, "attack": 1, "decay": 2, "sustain": 3, "release": 4}

@njit(cache=True)
def _env_loop(st, a_inc, s, cd, cr, out):
    """st = [stage, level]. Attack linear, decay and release exponential (G37)."""
    stage = st[0]; level = st[1]
    for i in range(len(out)):
        if stage == 1:
            level += a_inc
            if level >= 1.0:
                level = 1.0; stage = 2
        elif stage == 2:
            level = s + (level - s) * cd
            if level - s < 1e-4:
                level = s; stage = 3
        elif stage == 3:
            level = s
        elif stage == 4:
            level *= cr
            if level < 1e-5:
                level = 0.0; stage = 0
        out[i] = level
    st[0] = stage; st[1] = level

class Env:
    """Streaming ADSR. Inner loop is compiled when numba is installed."""
    def __init__(self, a, d, s, r):
        self.a = max(a, 1e-4); self.s = s
        self.cd = np.exp(-1.0 / (FS * max(d / 3, 1e-4)))
        self.cr = np.exp(-1.0 / (FS * max(r / 3, 1e-4)))
        self.st = np.array([0.0, 0.0])          # [stage, level]
    @property
    def stage(self):
        return [k for k, v in STAGE.items() if v == int(self.st[0])][0]
    def gate_on(self):
        self.st[0] = STAGE["attack"]
    def gate_off(self):
        if self.st[0] != STAGE["idle"]:
            self.st[0] = STAGE["release"]
    def block(self, n):
        if HAVE_NUMBA:
            out = np.empty(n)
            _env_loop(self.st, 1.0 / (FS * self.a), self.s, self.cd, self.cr, out)
            return out
        sl = self.st.tolist(); out = [0.0] * n
        _env_loop(sl, 1.0 / (FS * self.a), self.s, self.cd, self.cr, out)
        self.st[:] = sl
        return np.array(out)

def polyblep(t, dt):
    out = np.zeros_like(t)
    m = t < dt; x = t[m] / dt[m]; out[m] = 2 * x - x * x - 1
    m2 = t > 1 - dt; x = (t[m2] - 1) / dt[m2]; out[m2] = x * x + 2 * x + 1
    return out

@njit(cache=True)
def _ladder_loop(x, g, k, st, out):
    """Four tanh one-pole stages with resonance feedback. st = [y1,y2,y3,y4], updated in place."""
    y1 = st[0]; y2 = st[1]; y3 = st[2]; y4 = st[3]
    for i in range(len(x)):
        u = np.tanh(x[i] - k * y4)
        y1 += g[i] * (u - y1)
        y2 += g[i] * (np.tanh(y1) - y2)
        y3 += g[i] * (np.tanh(y2) - y3)
        y4 += g[i] * (np.tanh(y3) - y4)
        out[i] = y4
    st[0] = y1; st[1] = y2; st[2] = y3; st[3] = y4

def ladder_block(x, cut, k, st):
    """Filter one block. st is a numpy array [y1,y2,y3,y4] carried between blocks."""
    g = 1 - np.exp(-2 * np.pi * np.clip(cut, 20, FS * 0.45) / FS)
    if HAVE_NUMBA:
        out = np.empty(len(x))
        _ladder_loop(np.ascontiguousarray(x, dtype=np.float64), np.ascontiguousarray(g, dtype=np.float64),
                     float(k), st, out)
        return out, st
    # pure-Python fallback: plain lists are much faster than NumPy scalar indexing in a Python loop
    sl = st.tolist()
    out = [0.0] * len(x)
    _ladder_loop(x.tolist(), g.tolist(), float(k), sl, out)
    st[:] = sl
    return np.array(out), st

DEFAULT = dict(range="8", attack=0.005, decay=0.25, sustain=0.35, release=0.2,
               attack_pwm=0.01, decay_pwm=0.2, pw=0.5, pwm_amt=0.25,
               w_saw=1.0, w_pulse=0.0, w_sub=0.0, w_noise=0.0,
               cutoff=0.5, res=0.4, env_amt=0.6, lfo_rate=5.0, lfo_cut=0.0,
               vib_max=0.0, vca_mode="ENV", volume=0.8)
MIX = dict(saw=1.0, pulse=0.69, sub=0.57, noise=0.3)     # G39, G38

class Engine:
    def __init__(self, patch=None):
        self.p = dict(DEFAULT, **(patch or {}))
        self.stack = []                 # held MIDI notes, last one plays
        self.midi = None
        self.mod = 0.0                  # mod wheel 0..1 (CC1)
        self.bend = 0.0                 # pitch bend in semitones (+-2)
        self.res_cc = None              # CC71 override, 0..1
        self.cut_cc = None              # CC74 override, 0..1
        self.phase = 0.0; self.phase_sub = 0.0; self.lfo_phase = 0.0
        self.pwm_env = Env(self.p["attack_pwm"], self.p["decay_pwm"], 0.0, self.p["release"])
        self.amp_env = Env(self.p["attack"], self.p["decay"], self.p["sustain"], self.p["release"])
        self.ladder_st = np.zeros(4)
        self.base_cut = None

    # ---- MIDI-facing controls ----
    def note_on(self, midi):
        if midi in self.stack:
            self.stack.remove(midi)
        self.stack.append(midi)
        self._play(midi, retrigger=True)

    def note_off(self, midi):
        if midi in self.stack:
            self.stack.remove(midi)
        if not self.stack:
            self.amp_env.gate_off(); self.pwm_env.gate_off()
        elif midi == self.midi:
            self._play(self.stack[-1], retrigger=False)     # last-note priority, no retrigger

    def _play(self, midi, retrigger):
        self.midi = midi
        cut_pos = self.cut_cc if self.cut_cc is not None else self.p["cutoff"]
        bus = CUT_BUS_MIN + cut_pos * (CUT_BUS_MAX - CUT_BUS_MIN)
        self.base_cut = cutoff_hz(midi, bus)              # keyboard tracking, calibrated (1 oct/oct)
        if retrigger:
            self.amp_env.gate_on(); self.pwm_env.gate_on()

    def control_change(self, cc, value):
        v = value / 127.0
        if cc == 1:
            self.mod = v
        elif cc == 71:
            self.res_cc = v
        elif cc == 74:
            self.cut_cc = v
            if self.midi is not None:
                self._play(self.midi, retrigger=False)

    def pitch_bend(self, value):                 # value -8192..8191
        self.bend = 2.0 * value / 8192.0

    # ---- audio ----
    def process(self, n):
        if self.amp_env.stage == "idle" or self.midi is None:
            return np.zeros(n)
        p = self.p
        t = np.arange(n) / FS
        lfo_dt = np.full(n, p["lfo_rate"] / FS)
        ph_l = (self.lfo_phase + np.cumsum(lfo_dt)) % 1.0
        self.lfo_phase = ph_l[-1]
        lfo = 2 * np.abs(2 * ph_l - 1) - 1                  # G43 triangle
        env_pw = self.pwm_env.block(n)
        env = self.amp_env.block(n)
        vib = self.mod * p["vib_max"]
        f = note_hz(self.midi, p["range"]) * 2 ** ((vib * lfo + self.bend) / 12.0)
        dt = f / FS
        ph = (self.phase + np.cumsum(dt)) % 1.0
        self.phase = ph[-1]
        ph2 = (self.phase_sub + np.cumsum(dt / 2)) % 1.0
        self.phase_sub = ph2[-1]
        duty = np.clip(0.5 * p["pw"] + p["pwm_amt"] * env_pw, 0.02, 0.98)
        saw = 2 * ph - 1 - polyblep(ph, dt)
        pulse = np.where(ph < duty, 1.0, -1.0) - polyblep(ph, dt) + polyblep((ph - duty) % 1.0, dt)
        sub = np.where(ph2 < 0.5, 1.0, -1.0) - polyblep(ph2, dt / 2) + polyblep((ph2 - 0.5) % 1.0, dt / 2)
        noise = np.random.default_rng().uniform(-1, 1, n)
        src = (p["w_saw"] * MIX["saw"] * saw + p["w_pulse"] * MIX["pulse"] * pulse
               + p["w_sub"] * MIX["sub"] * sub + p["w_noise"] * MIX["noise"] * noise)
        cut = self.base_cut * 2 ** (p["env_amt"] * 4.0 * env + p["lfo_cut"] * lfo)
        res = self.res_cc if self.res_cc is not None else p["res"]
        k = min(4.2 * res / 0.785, 5.0)
        filt, self.ladder_st = ladder_block(src * 0.5, cut, k, self.ladder_st)
        gain = env if p["vca_mode"] == "ENV" else np.ones(n) * (1.0 if self.stack else 0.0)
        return filt * gain * p["volume"]

if __name__ == "__main__":
    import time
    print("numba:", "on" if HAVE_NUMBA else "off (pure Python fallback)", " block:", BLOCK)
    eng = Engine(dict(cutoff=0.71, res=0.45, env_amt=0.7, w_saw=1.0, w_sub=0.4, decay=0.3, sustain=0.2))
    out = []
    eng.note_on(45)
    t0 = time.time()
    for _ in range(int(1.0 * FS / BLOCK)):
        out.append(eng.process(BLOCK))
    eng.note_off(45)
    for _ in range(int(0.6 * FS / BLOCK)):
        out.append(eng.process(BLOCK))
    dt = time.time() - t0
    x = np.concatenate(out)
    print(f"processed {len(x)/FS:.2f} s in {dt:.2f} s -> {dt/(len(x)/FS):.3f} x real time")
    print("finite:", np.isfinite(x).all(), " peak:", round(float(np.abs(x).max()), 3))
    seg = x[int(0.2*FS):int(0.9*FS)]
    F = np.abs(np.fft.rfft(seg*np.hanning(len(seg)), n=8*len(seg))); fr = np.fft.rfftfreq(8*len(seg), 1/FS)
    b = (fr > 30) & (fr < 400)
    print("note A2 (MIDI 45) dominant:", round(float(fr[b][np.argmax(F[b])]), 1), "Hz (expect 110.5)")
