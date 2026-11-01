# SH-101 emulator

Start here. This is the SH-101 emulator: a guess-supported model of the SH-101 filter, VCO, VCA and keyboard path, built from the Roland service manual, the Roland page 7 circuit diagram, the AS3109 datasheet, and photos.

## Files

| File | What it is |
|---|---|
| `FINDINGS.md` | What the scans confirm, with evidence and confidence for each item |
| `guess_ledger.md` | Every guess (G1–G18), its effect, and the photo that would settle it |
| `PHOTO_PLAN.md` | Photos to take on the unit, ordered by priority |
| `measurement_checklist.md` | DC and sweep measurements for when the unit is open |
| `sensitivity_results.txt` | How much each guess changes the measurable result |
| `sh101_vcf.py` | Component-level small-signal model of the transcribed IC14 network |
| `sh101_vcf_netlist.json` | The transcribed network as data |
| `sh101_vcf_smallsignal.cir` | SPICE deck of the same network (not yet run in ngspice) |
| `sh101_guessed.py` | Voice model with the guessed VCO and cutoff calibration |
| `vco_cem3340.py` | VCO model using the CEM3340 datasheet values |
| `reference_check.py` | Tune-reference arithmetic (G25) |
| `vco_pulse.py` | Pulse-width VCO model |
| `as3109_ladder.py` | Early behavioral ladder (superseded by `sh101_vcf.py`) |
| `sensitivity.py` | Script that produces the sensitivity table |
| `export_netlist.py` | Writes the JSON and SPICE files from the model |
| `taste_of_sh101.py` | First listening preview |
| `sh101_emulator.py` | The SH-101 emulator: full voice and three-patch demo |
| `EMULATOR_GUESSES.md` | Guesses G36–G44 specific to the emulator |
| `play_notes.py` | Renders a text note list (`midi start duration` per line) with a patch: `python3 play_notes.py notes.txt out.wav bass` |
| `example_riff.txt` | Example note list for `play_notes.py` |
| `sh101_engine.py` | Streaming (live) version of the emulator voice |
| `sh101_phone.html` | Phone web app: on-screen keyboard, controls, and Web MIDI. Open it from a web address (HTTPS), not a local file. |
| `sh101_core.js` | JavaScript core used by the phone page: arpeggio, legato, portamento, transpose, bender, hold, and the LFO, VCO, sub, VCA and envelope-trigger switches |
| `sh101_midi.py` | Plays the emulator from a MIDI keyboard: `python3 sh101_midi.py --list`, then `--port <name>`; `--block 1024` if you hear clicks |

## Audio previews
- `sh101_emulator_demo.wav`: the SH-101 emulator demo (bass, PWM lead, resonant whistle)
- `sh101_taste.wav`: first behavioral preview, arbitrary calibration
- `sh101_guessed.wav`: calibrated VCO and cutoff from the guesses
- `sh101_pulse_pwm.wav`: pulse wave with envelope PWM

## How to run
Needs Python 3 with numpy and scipy. From this folder:
    python3 sh101_guessed.py      # voice model and preview
    python3 sh101_vcf.py          # component model checks
    python3 sensitivity.py        # sensitivity table

## Status (updated)
- Datasheets used: AS3109 (filter chip, clone) and CEM3340/3345 (VCO chip, Curtis). The CEM3340 datasheet resolved the PWM, scale-error and tempco questions.
- Best estimates for every open item are in `guess_ledger.md` (section "Best estimates"). Each has a confidence level.
- Re-reading the clean circuit diagram resolved G5 (VCA load = 1 kΩ), G4, G10, G24, G27 and the cutoff-sign question, and identified R104 as the keyboard resistor. Two earlier statements were wrong and are corrected in guess_ledger.md (tune-reference node, and the VR5 / TR24 / TR25 roles).
- Keyboard tracking (G13) is closed by calibration: VR-8 is the tracking trim (G34), so tracking is exact at the adjusted setting.
- Remaining open items: FREQ slider span (G14), TH1 (G6), R100's far end, and the MOD polarity through TR42 (G35).
- Audio previews use the estimates. Listening to them is the fastest way to see if a guess is wrong.

## Status (earlier)
- Filter pin map (IC14): confirmed against the datasheet.
- Filter component values and resonance path: read from the scan, with a few assumptions.
- Output-level prediction at high resonance: depends on the VCA load guess (G5).
- VCO: pitch calibration and pulse width modelled from guesses; the CEM3340 internals are not simulated.
- Cutoff summing: topology read from the scan; input assignments and polarity are guesses (G7, G16).
- Nothing has been checked on a real unit yet.
