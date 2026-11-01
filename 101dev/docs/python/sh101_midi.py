"""
Play the SH-101 emulator from a MIDI keyboard.

Requirements (on your computer):
    pip install mido python-rtmidi sounddevice numpy scipy

Usage:
    python3 sh101_midi.py --list                 # show MIDI inputs
    python3 sh101_midi.py --port "Your Keyboard" # play live (uses default audio output)
    python3 sh101_midi.py --port 0 --patch bass  # patch: bass, pwm, whistle
    python3 sh101_midi.py --port 0 --block 1024  # bigger buffer if you hear clicks

Controls (standard MIDI):
    Notes        monophonic, last note priority
    Mod wheel    CC1  vibrato depth
    CC71         resonance (overrides the patch value)
    CC74         cutoff (overrides the patch value)
    Pitch bend   +-2 semitones
"""
import argparse
import threading
import numpy as np
from sh101_engine import Engine, BLOCK, FS

PATCHES = {
    "bass": dict(cutoff=0.71, res=0.45, env_amt=0.7, w_saw=1.0, w_sub=0.4, decay=0.3, sustain=0.2, vib_max=0.02),
    "pwm": dict(w_saw=0.0, w_pulse=1.0, pw=0.4, pwm_amt=0.35, cutoff=0.55, res=0.35, env_amt=0.3,
                lfo_rate=5.5, vib_max=0.02, attack=0.2, decay=0.6, sustain=0.6, release=0.4),
    "whistle": dict(w_saw=0.05, cutoff=0.61, res=0.9, env_amt=0.0, lfo_cut=0.08, lfo_rate=4.0,
                    attack=0.02, decay=0.4, sustain=0.6, release=0.3, vca_mode="GATE"),
}

class Player:
    """Routes MIDI messages to the engine. Thread-safe: MIDI and audio threads share the engine."""
    def __init__(self, engine):
        self.engine = engine
        self.lock = threading.Lock()

    def handle(self, msg):
        """msg: a mido-style message with .type and fields (or a dict in tests)."""
        get = (lambda k, d=None: msg.get(k, d)) if isinstance(msg, dict) else (lambda k, d=None: getattr(msg, k, d))
        kind = get("type")
        with self.lock:
            if kind == "note_on" and get("velocity", 0) > 0:
                self.engine.note_on(get("note"))
            elif kind in ("note_off",) or (kind == "note_on" and get("velocity", 0) == 0):
                self.engine.note_off(get("note"))
            elif kind == "control_change":
                self.engine.control_change(get("control"), get("value"))
            elif kind == "pitchwheel":
                self.engine.pitch_bend(get("pitch"))

    def render(self, frames):
        with self.lock:
            return self.engine.process(frames)

def run(port_name, patch_name, block=BLOCK):
    import mido
    import sounddevice as sd
    engine = Engine(PATCHES[patch_name])
    player = Player(engine)

    def audio_cb(outdata, frames, time_info, status):
        block = player.render(frames).astype(np.float32)
        outdata[:, 0] = np.clip(block, -1, 1)

    with sd.OutputStream(samplerate=FS, channels=1, blocksize=block, callback=audio_cb):
        with mido.open_input(port_name, callback=player.handle):
            print(f"Playing '{patch_name}' from '{port_name}' (buffer {block} samples, "
                  f"about {1000*block/FS:.0f} ms). Press Ctrl+C to stop.")
            try:
                while True:
                    sd.sleep(1000)
            except KeyboardInterrupt:
                print("stopped")

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="list MIDI inputs and exit")
    ap.add_argument("--port", help="MIDI input name (or part of it)")
    ap.add_argument("--patch", default="bass", choices=list(PATCHES))
    ap.add_argument("--block", type=int, default=BLOCK,
                    help="audio buffer in samples (default 512). Raise to 1024 if you hear clicks.")
    args = ap.parse_args()
    if args.list:
        import mido
        for name in mido.get_input_names():
            print(name)
        return
    if not args.port:
        ap.error("give --port (use --list to see inputs)")
    import mido
    names = [n for n in mido.get_input_names() if args.port.lower() in n.lower()]
    if not names:
        raise SystemExit(f"no MIDI input matching {args.port!r}; run with --list")
    run(names[0], args.patch, args.block)

if __name__ == "__main__":
    main()
