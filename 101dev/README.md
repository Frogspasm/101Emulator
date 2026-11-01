# 101dev: SH-101 emulator working folder

| Path | What it is |
|---|---|
| `index.html` | Phone app, built from `docs/sh101_core.js` and `tools/index.template.html` by `node tools/build_index.js`. Do not edit it by hand. Serve over HTTP(S); it will not play from a file:// address. |
| `docs/sh101_core.js` | Canonical DSP core. `index.html` should be rebuilt from this. |
| `docs/HANDOFF.md` | Brief for continuing development. Read first. |
| `docs/guess_ledger.md` | Every guess (G1 to G70), with basis, confidence and the check that settles it. |
| `docs/FINDINGS.md` | What the scans and datasheets confirm. |
| `docs/README.md` | Earlier project file map (names some files no longer in the repo). |
| `tools/build_index.js`, `tools/index.template.html` | Rebuild `index.html` (both copies of the core come from `docs/sh101_core.js`). |
| `tools/render_notes.js` | Renders a note list to WAV with the core: `node tools/render_notes.js notes.txt out.wav bass` |
| `analysis/` | Component-level circuit model and the checks behind the ledger's numbers. Needs Python 3 with numpy and scipy. |

## Notes file format

One note per line: `midi_note start_seconds duration_seconds`. Lines starting with `#` are comments.

## Analysis scripts

Run from `analysis/`:

- `python3 sh101_vcf.py`: component-level VCF checks (resonance threshold, output levels, CV divider).
- `python3 sensitivity.py`: which guesses change the result most.
- `python3 reference_check.py`: CEM3340 frequency law and scale trim.

The Python voice engine and MIDI player were removed. They duplicated the core and had fallen behind it. They remain in git history.
