# SH-101 Emulator

A browser-based, monophonic emulation of the Roland SH-101 signal path, built on the Web Audio API. It is a single self-contained file with no dependencies or build step.

## Running it

Open `index.html` in a modern browser (Chrome, Edge, Firefox or Safari). Click the **Audio off** button or press any note key to start the audio engine.

## Controls

| Section  | Control | What it does |
|----------|---------|--------------|
| VCO      | Saw / Pulse on/off | Enables the sawtooth and pulse oscillators |
| VCO      | Sub | Level of a square wave one octave below the played note |
| VCO      | Noise | White-noise level |
| VCO      | Pulse width | Duty cycle of the pulse wave (5–95 %) |
| VCF      | Cutoff | Lowpass cutoff (20 Hz – 12 kHz, exponential) |
| VCF      | Resonance | Q of the filter stages |
| VCF      | Env amount | How far the envelope pushes the cutoff |
| VCF      | Key track | Cutoff follows the played note (0 = fixed, 100 % = full tracking) |
| VCF      | LFO → VCF | LFO depth on the cutoff |
| Envelope | Attack / Decay / Sustain / Release | ADSR shaping the VCA and the filter |
| Envelope | Gate / Trig | **Gate**: normal ADSR, held while the key is down. **Trig**: one-shot attack and decay, ignoring the key's hold and the sustain level |
| LFO      | Rate, Wave (Tri / Square / Saw) | LFO speed and shape |
| LFO      | LFO → pitch | Vibrato depth in cents |
| Master   | Glide | Portamento time between notes |
| Master   | Volume | Output level |

Buttons: **Oct −/+** shift the keyboard range (±2 octaves). **Panic** releases all notes.

### Keyboard

- Computer keys `A W S E D F T G Y H U J K O L P` play 16 consecutive semitones, from C up to D♯ one octave higher (`A` = C, `W` = C♯, and so on).
- `Z` / `X` shift the octave down / up.
- The on-screen keyboard works with mouse and touch.

## Monophonic behaviour

The SH-101 is monophonic, and so is this emulator:

- Last-note priority: the most recently pressed key sounds.
- Legato: pressing a second key while one is held glides to it without retriggering the envelope (Gate mode).
- Releasing the top key falls back to the most recently held key still down.

## Known differences from the hardware

- The lowpass is two cascaded 12 dB/oct resonant biquad filters, giving 24 dB/oct. It does not model the transistor ladder's saturation or its resonance behaviour.
- Pulse width is static. The LFO cannot modulate it, and the wave is regenerated only when the knob changes.
- The LFO has no delay or random waveform.
- There is no oscillator drift, no sync, and no tuning or temperature variation.
- The pulse wave has its DC component removed, as with an AC-coupled output.

## Files

- `index.html`: the whole emulator (markup, styles and script).
- `README.md`: this file.
