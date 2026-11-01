"""
Render a note list with an SH-101 emulator patch.

Usage:
    python3 play_notes.py notes.txt out.wav [patch]

notes.txt has one note per line:  midi_note  start_seconds  duration_seconds
Lines starting with # are comments. Example:
    # A minor riff
    45  0.0  0.4
    48  0.5  0.4
    52  1.0  0.8

Patches: bass, pwm, whistle (defaults to bass). Edit PATCHES below to make your own.
"""
import sys
from scipy.io import wavfile
import sh101_emulator as em

PATCHES = {
    "bass":
            dict(em.BASE, cutoff=0.71, res=0.45, env_amt=0.7, w_saw=1.0, w_sub=0.4, decay=0.3, sustain=0.2),
    "pwm": dict(em.BASE, w_saw=0.0, w_pulse=1.0, pw=0.4, pwm_amt=0.35, cutoff=0.55, res=0.35,
                env_amt=0.3, lfo_rate=5.5, vib_oct=0.01, attack=0.2, decay=0.6, sustain=0.6, release=0.4),
    "whistle": dict(em.BASE, w_saw=0.05, cutoff=0.61, res=0.9, env_amt=0.0, lfo_cut=0.08,
                    lfo_rate=4.0, attack=0.02, decay=0.4, sustain=0.6, release=0.3, vca_mode="GATE"),
}

def load_notes(path):
    seq = []
    for line in open(path):
        line = line.split("#")[0].strip()
        if not line:
            continue
        midi, start, dur = line.split()
        seq.append((int(midi), float(start), float(dur)))
    if not seq:
        raise SystemExit("no notes found in " + path)
    return seq

if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    notes = load_notes(sys.argv[1])
    out = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else "bass"
    if name not in PATCHES:
        raise SystemExit(f"unknown patch {name!r}; choose from {', '.join(PATCHES)}")
    audio = em.render(notes, PATCHES[name])
    wavfile.write(out, em.FS, (em.norm(audio) * 32767).astype("int16"))
    print(f"wrote {out} ({len(audio)/em.FS:.1f} s) with patch '{name}'")
