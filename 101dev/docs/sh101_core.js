/* SH-101 emulator core (JavaScript port of sh101_engine.py). Same models and guesses (G36-G44).
   Works in a browser AudioWorklet and in Node for testing. No DOM access. */
(function (root) {
  const A4 = 442.0;
  const K4 = 0.435, FC0 = 250.0, VC = 0.019, PIN9 = 0.1110;
  const KYB = VC / PIN9;                       // exact 1 oct/oct keyboard tracking (VR-8 calibration)
  const CUT_MIN = 0.589, CUT_MAX = -1.288;     // slider: 10 Hz (bottom) .. 20 kHz (top), spec
  const MIX = { saw: 1.0, pulse: 0.69, sub: 0.57, noise: 0.3 };   // G39, G38

  const kcv = (m) => 0.417 + (m - 53) / 12.0;  // service manual: F3 = 0.417 V, 1 V/oct
  function bus(p) { return CUT_MIN + p * (CUT_MAX - CUT_MIN); }
  function cutoffHz(midi, p, follow) {
    const f = follow === undefined ? 1 : follow;               // Key Follow knob, 0..1 (Roland spec)
    const v9 = PIN9 * (bus(p) - f * KYB * (kcv(midi) - kcv(60)));
    return K4 * FC0 * Math.pow(2, -v9 / VC);
  }
  function noteHz(midi, rangeOct, cents) { return A4 * Math.pow(2, (midi - 69) / 12) * Math.pow(2, rangeOct) * Math.pow(2, (cents || 0) / 1200); }

  function blep(t, dt) {
    if (t < dt) { const x = t / dt; return 2 * x - x * x - 1; }
    if (t > 1 - dt) { const x = (t - 1) / dt; return x * x + 2 * x + 1; }
    return 0;
  }

  class Env {                                  // G36, G37: linear attack, exponential decay and release
    constructor(fs, a, d, s, r) {
      this.fs = fs; this.a = Math.max(a, 1e-4); this.s = s;
      this.cd = Math.exp(-1 / (fs * Math.max(d / 3, 1e-4)));
      this.cr = Math.exp(-1 / (fs * Math.max(r / 3, 1e-4)));
      this.stage = 0; this.level = 0;          // 0 idle, 1 attack, 2 decay, 3 sustain, 4 release
    }
    setParams(a, d, s, r) {                 // change times/levels without resetting the current note
      this.a = Math.max(a, 1e-4); this.s = s;
      this.cd = Math.exp(-1 / (this.fs * Math.max(d / 3, 1e-4)));
      this.cr = Math.exp(-1 / (this.fs * Math.max(r / 3, 1e-4)));
    }
    on() { this.stage = 1; }
    off() { if (this.stage !== 0) this.stage = 4; }
    next() {
      if (this.stage === 1) { this.level += 1 / (this.fs * this.a); if (this.level >= 1) { this.level = 1; this.stage = 2; } }
      else if (this.stage === 2) { this.level = this.s + (this.level - this.s) * this.cd; if (this.level - this.s < 1e-4) { this.level = this.s; this.stage = 3; } }
      else if (this.stage === 3) { this.level = this.s; }
      else if (this.stage === 4) { this.level *= this.cr; if (this.level < 1e-5) { this.level = 0; this.stage = 0; } }
      return this.level;
    }
  }

  const DEFAULT = { rangeOct: 0, attack: 0.005, decay: 0.25, sustain: 0.35, release: 0.2,
    attackPwm: 0.01, decayPwm: 0.2, pw: 0.5, pwmAmt: 0.25,
    wSaw: 1, wPulse: 0, wSub: 0, wNoise: 0, cutoff: 0.5, res: 0.4, envAmt: 0.6,
    lfoRate: 5.0, lfoCut: 0, vibMax: 0, vcaGate: false, volume: 0.8,
    legato: false, portaTime: 0, transpose: 0, arpMode: "off", arpBpm: 120,
    // switches (G50-G54)
    lfoWave: "triangle",    // "square" | "triangle" | "noise" | "random"
    vcoWave: "both",        // not a Roland switch: the source mixer levels control saw and pulse (G51 corrected)
    subOct: "1",            // "1" = square 1 oct down, "2" = square 2 oct down, "2p" = pulse 2 oct down (panel, G62)
    vcaMode: "ENV",         // "ENV" | "GATE"
    envTrig: "gate",        // "gate" | "gatetrig" | "lfo"
    pwmSrc: "env",          // PWM source: "env" | "lfo" | "man" (panel switch LFO / MAN / ENV, G56)
    portaMode: "auto",      // portamento: "auto" | "off" | "on" (panel AUTO / OFF / ON, G57)
    keyFollow: 1,           // KYBD / Key Follow slider, 0..1
    tuneCents: 0,           // TUNE knob, +-50 cents
    vcoBend: 1,             // Bend VCO slider: 1 = +-2 semitones at full lever
    vcfBend: 0 };           // Bend VCF slider: 1 = +-1 octave at full lever (G69)

  class Voice {
    constructor(fs, patch) {
      this.fs = fs; this.p = Object.assign({}, DEFAULT, patch || {});
      this.stack = []; this.physical = new Set(); this.hold = false;
      this.midi = null; this.mod = 0; this.resCC = null; this.cutCC = null;
      this.ph = 0; this.phSub = 0; this.phLfo = 0; this.lfoHold = 0; this.bendNorm = 0;
      this.pwmEnv = new Env(fs, this.p.attackPwm, this.p.decayPwm, 0, this.p.release);
      this.ampEnv = new Env(fs, this.p.attack, this.p.decay, this.p.sustain, this.p.release);
      this.y = [0, 0, 0, 0]; this.baseCut = 0;
      this.pitch = null; this.target = null; this.glideAllowed = false;
      this.arpIdx = 0; this.arpDir = 1; this.arpCount = 0; this.arpGateAt = 0; this.arpFirst = false;
    }
    rebuildEnvs() {
      this.pwmEnv = new Env(this.fs, this.p.attackPwm, this.p.decayPwm, 0, this.p.release);
      this.ampEnv = new Env(this.fs, this.p.attack, this.p.decay, this.p.sustain, this.p.release);
    }
    setPatch(patch) {
      this.p = Object.assign({}, this.p, patch);
      const p = this.p;
      this.pwmEnv.setParams(p.attackPwm, p.decayPwm, 0, p.release);
      this.ampEnv.setParams(p.attack, p.decay, p.sustain, p.release);
      if (this.midi !== null) this.play(this.midi, false);
    }
    arpSteps() { return Math.max(1, Math.round(this.fs * 60 / this.p.arpBpm / 4)); }
    play(midi, retrigger) {
      const eff = midi + this.p.transpose;
      this.midi = midi; this.target = eff;
      if (this.pitch === null) this.pitch = eff;
      const pos = this.cutCC !== null ? this.cutCC : this.p.cutoff;
      this.baseCut = cutoffHz(eff, pos, this.p.keyFollow);
      if (retrigger && this.p.envTrig !== "lfo") { this.ampEnv.on(); this.pwmEnv.on(); }
    }
    noteOn(midi) {
      this.physical.add(midi);
      const i = this.stack.indexOf(midi); if (i >= 0) this.stack.splice(i, 1);
      const hadNotes = this.stack.length > 0;
      this.stack.push(midi);
      if (this.p.arpMode !== "off") {
        if (!hadNotes) { this.arpCount = this.arpSteps(); this.arpFirst = true; }
        return;
      }
      const retrig = this.p.envTrig === "gatetrig" ? true : !(this.p.legato && hadNotes);
      // portamento: ON glides every note; AUTO glides only when a key is played while others are held; OFF never
      this.glideAllowed = this.p.portaMode === "on" || (this.p.portaMode === "auto" && hadNotes);
      this.play(midi, retrig);
    }
    noteOff(midi) {
      this.physical.delete(midi);
      if (this.hold) return;                                // hold keeps the notes sounding
      this.release(midi);
    }
    release(midi) {
      const i = this.stack.indexOf(midi); if (i >= 0) this.stack.splice(i, 1);
      if (this.stack.length === 0) {
        if (this.p.envTrig !== "lfo") { this.ampEnv.off(); this.pwmEnv.off(); }
        this.arpCount = 0; return;
      }
      if (this.p.arpMode === "off" && midi === this.midi) this.play(this.stack[this.stack.length - 1], false);
    }
    setHold(on) {
      this.hold = !!on;
      if (!this.hold) {                                     // releasing hold lets go of keys that are no longer down
        const keep = this.stack.filter(m => this.physical.has(m));
        const dropped = this.stack.filter(m => !this.physical.has(m));
        this.stack = keep;
        if (this.stack.length === 0) { if (this.p.envTrig !== "lfo") { this.ampEnv.off(); this.pwmEnv.off(); } this.arpCount = 0; }
        else if (dropped.length && this.p.arpMode === "off" && this.midi !== null && !keep.includes(this.midi)) this.play(keep[keep.length - 1], false);
      }
    }
    control(cc, value) {
      const v = value / 127;
      if (cc === 1) this.mod = v;
      else if (cc === 71) this.resCC = v;
      else if (cc === 74) { this.cutCC = v; if (this.midi !== null) this.play(this.midi, false); }
    }
    pitchBend(value) { this.bendNorm = Math.max(-1, Math.min(1, value / 8192)); }

    arpAdvance() {
      const notes = this.stack.slice().sort((a, b) => a - b);
      const n = notes.length, mode = this.p.arpMode;
      if (this.arpFirst) { this.arpFirst = false; this.arpDir = 1; this.arpIdx = mode === "down" ? n - 1 : 0; }
      else if (mode === "up") this.arpIdx = (this.arpIdx + 1) % n;
      else if (mode === "down") this.arpIdx = (this.arpIdx - 1 + n) % n;
      else {
        if (n > 1) {
          this.arpIdx += this.arpDir;
          if (this.arpIdx >= n - 1) { this.arpIdx = n - 1; this.arpDir = -1; }
          if (this.arpIdx <= 0) { this.arpIdx = 0; this.arpDir = 1; }
        } else this.arpIdx = 0;
      }
      if (this.arpIdx >= n) this.arpIdx = 0;
      this.play(notes[this.arpIdx], true);
    }

    render(out, n) {
      const p = this.p, fs = this.fs;
      if (this.stack.length === 0 && this.ampEnv.stage === 0) { for (let i = 0; i < n; i++) out[i] = 0; return; }
      if (this.midi === null && this.stack.length === 0) { for (let i = 0; i < n; i++) out[i] = 0; return; }
      const res = this.resCC !== null ? this.resCC : p.res;
      const k = Math.min(4.2 * res / 0.785, 5.0);
      const vib = this.mod * p.vibMax;
      const gateOn = this.stack.length > 0 ? 1 : 0;
      const glideCoef = p.portaTime > 0 ? 1 - Math.exp(-1 / (fs * Math.max(p.portaTime / 3, 1e-4))) : 1;
      const arpOn = p.arpMode !== "off" && this.stack.length > 0;
      const stepLen = this.arpSteps();
      const sawOn = p.vcoWave !== "pulse" ? 1 : 0, pulseOn = p.vcoWave !== "saw" ? 1 : 0;
      const subDiv = (p.subOct === "2" || p.subOct === "2p") ? 4 : 2, subOn = 1;
      const subPulse = p.subOct === "2p";
      const gateMode = p.vcaMode === "GATE" || p.vcaGate;
      for (let i = 0; i < n; i++) {
        if (arpOn) {
          this.arpCount++;
          if (this.arpCount >= stepLen) { this.arpCount = 0; this.arpGateAt = Math.round(stepLen * 0.6); this.arpAdvance(); }
          if (this.arpCount === this.arpGateAt) { this.ampEnv.off(); this.pwmEnv.off(); }
        }
        if (this.pitch !== null && this.target !== null) {
          if (this.glideAllowed && p.portaTime > 0) this.pitch += (this.target - this.pitch) * glideCoef;
          else this.pitch = this.target;
        }
        const ph0 = this.phLfo;
        this.phLfo = (ph0 + p.lfoRate / fs) % 1;
        const wrapped = this.phLfo < ph0;
        if (wrapped) this.lfoHold = Math.random() * 2 - 1;      // random: new level each LFO cycle
        if (wrapped && p.envTrig === "lfo") { this.ampEnv.on(); this.pwmEnv.on(); }
        let lfo;
        if (p.lfoWave === "square") lfo = this.phLfo < 0.5 ? 1 : -1;
        else if (p.lfoWave === "noise") lfo = Math.random() * 2 - 1;
        else if (p.lfoWave === "random") lfo = this.lfoHold;
        else lfo = 2 * Math.abs(2 * this.phLfo - 1) - 1;        // triangle (G43)
        const envPwm = this.pwmEnv.next();
        const env = this.ampEnv.next();
        const f = noteHz(this.pitch === null ? 69 : this.pitch, p.rangeOct, p.tuneCents) * Math.pow(2, (vib * lfo + 2 * this.bendNorm * p.vcoBend) / 12);
        const dt = f / fs;
        this.ph = (this.ph + dt) % 1; const t = this.ph;
        this.phSub = (this.phSub + dt / subDiv) % 1; const ts = this.phSub;
        const pwmMod = p.pwmSrc === "env" ? envPwm : p.pwmSrc === "lfo" ? lfo : 0;   // MAN = no modulation
        const duty = Math.min(0.98, Math.max(0.02, 0.5 * p.pw + p.pwmAmt * pwmMod));
        const saw = 2 * t - 1 - blep(t, dt);
        const pulse = (t < duty ? 1 : -1) - blep(t, dt) + blep((t - duty + 1) % 1, dt);
        const subDuty = subPulse ? 0.25 : 0.5;                 // G62: pulse sub taken as 25% width
        const sub = (ts < subDuty ? 1 : -1) - blep(ts, dt / subDiv) + blep((ts - subDuty + 1) % 1, dt / subDiv);
        const noise = Math.random() * 2 - 1;
        const src = sawOn * p.wSaw * MIX.saw * saw + pulseOn * p.wPulse * MIX.pulse * pulse
                  + subOn * p.wSub * MIX.sub * sub + p.wNoise * MIX.noise * noise;
        const cut = this.baseCut * Math.pow(2, p.envAmt * 4.0 * env + p.lfoCut * lfo + this.bendNorm * p.vcfBend);
        const g = 1 - Math.exp(-2 * Math.PI * Math.min(Math.max(cut, 20), fs * 0.45) / fs);
        const x = src * 0.5;
        const y = this.y;
        const u = Math.tanh(x - k * y[3]);
        y[0] += g * (u - y[0]);
        y[1] += g * (Math.tanh(y[0]) - y[1]);
        y[2] += g * (Math.tanh(y[1]) - y[2]);
        y[3] += g * (Math.tanh(y[2]) - y[3]);
        const gain = gateMode ? gateOn : env;                   // G44 / VCA switch
        out[i] = y[3] * gain * p.volume;
      }
    }
  }

  const PATCHES = {
    bass: { cutoff: 0.71, res: 0.45, envAmt: 0.7, wSaw: 1, wSub: 0.4, decay: 0.3, sustain: 0.2, vibMax: 0.02 },
    pwm: { wSaw: 0, wPulse: 1, pw: 0.4, pwmAmt: 0.35, cutoff: 0.55, res: 0.35, envAmt: 0.3,
           lfoRate: 5.5, vibMax: 0.02, attack: 0.2, decay: 0.6, sustain: 0.6, release: 0.4 },
    whistle: { wSaw: 0.05, cutoff: 0.61, res: 0.9, envAmt: 0, lfoCut: 0.08, lfoRate: 4.0,
               attack: 0.02, decay: 0.4, sustain: 0.6, release: 0.3, vcaGate: true },
  };

  const api = { Voice, Env, cutoffHz, noteHz, kcv, PATCHES, DEFAULT, MIX };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.SH101 = api;
})(typeof globalThis !== "undefined" ? globalThis : (typeof self !== "undefined" ? self : this));
