# SH-101 emulator: handoff brief for Claude Code

## Goal
A phone-playable emulator of the Roland SH-101 that models the real circuit as closely as the
available documents allow. The owner plays it from a MIDI keyboard (Android Chrome) or the on-screen keys.
Every value that is not measured or documented is a logged guess. Guesses must stay visible.

## Read first
1. `README.md`: file map and status.
2. `guess_ledger.md`: every guess (G1 to G70), its basis, confidence, and the check that would settle it.
   Treat this as the source of truth for what is assumed.
3. `FINDINGS.md`: what the scans and datasheets confirm, with evidence.
4. `EMULATOR_GUESSES.md`: guesses specific to the emulator voice (G36 to G44).

## Current deliverables
- `sh101_phone.html`: the phone app. Single file: layout, controls, Web MIDI, on-screen keyboard,
  AudioWorklet loader. The DSP core is inlined twice (see Build below).
- `sh101_core.js`: JavaScript DSP core (Voice, Env, ladder filter, oscillators, arp, portamento,
  hold, switches, knobs' underlying parameters). Canonical copy of the DSP.
- `sh101_engine.py`, `sh101_emulator.py`, `play_notes.py`, `sh101_midi.py`: Python versions for
  offline rendering and desktop MIDI. The Python side has NOT been updated for the newer features
  (arp, legato, portamento, hold, switches, bend, key follow, tune). Treat it as legacy unless asked.
- `sh101_guessed.py`, `keyboard_vca.py`, `sh101_vcf.py`, `vco_cem3340.py`, `vco_pulse.py`:
  model building blocks used by the Python side. Constants (CUT_BUS_MIN/MAX, KYB_GAIN, etc.)
  are mirrored in the JS core.
- `measurement_checklist.md`, `PHOTO_PLAN.md`: checks to run on the owner's physical unit.
- Demo WAVs: `sh101_emulator_demo_v1.wav` (old slider mapping, approved sound), `..._v3.wav`
  (current mapping, approved). `v2` is superseded.

## Build
`sh101_phone.html` contains the core in two places:
- a plain `<script>` block (first script), and
- a `<script type="text/plain" id="core-src">` block, which the worklet reads as text.
After editing `sh101_core.js`, replace both copies. The script between `<script>\n` and `\n</script>`
is the core; the `core-src` block is the same text with `</script` escaped as `<\/script`.
Keep the `__CORE_SLOT__` placeholder inside the `WORKLET` template literal.

## Verification done so far
- Node tests (no browser): pitch (A4 = 442 Hz at 8 ft), cutoff tracking (exactly 2.000 per octave at
  full key follow), envelope times vs spec ranges, portamento glide, legato (no retrigger), transpose,
  arpeggio order (up, down, up/down), hold, LFO trigger count, VCF/VCO bend ranges, sub 2-oct pulse,
  VCA gate vs ENV, and the AudioWorklet processor run in a stub harness.
- Syntax checks (`node --check`) on the page scripts after each edit.
- Element-ID check: every `getElementById` id used by the scripts exists in the HTML.

## NOT verified (do this first)
- The page has never been opened in a real browser by the agent. The owner has heard the
  sound and used the MIDI keyboard, so the basics work on their phone. The layout, slider
  grab zone (30 px), and knob behaviour are checked only by owner feedback.
- numba is optional in the Python engine. Never run here (no network). Fallback path tested.
- `pip install` and MIDI hardware were never tested by the agent.

## Known issues and decisions to review
- Two implementations (Python and JS) of the same models will drift. Consider making the JS
  core the only one, or generating the Python from it.
- Presets (`PATCHES`) are duplicated in `sh101_core.js` and `sh101_midi.py`/`sh101_emulator.py`.
- The knob style is matched to a screenshot of AcidBox (yellow face, dark indicator, red-orange
  value arc). The AcidBox source was not available, so exact colours are approximate.
- Slider styling: custom vertical sliders via CSS rotation. The PWM switch uses class `half`
  (89 px). The Sub switch uses a 3-position slider with `data-names` labels.
- The VCO wave switch was removed (not a Roland control). The source mixer levels do that job.

## Open items, most useful first
1. Browser check of the layout on a phone (sliders vertical, sections, TUNE + MODULATOR line,
   VCO line, source mixer line, arp row). Look for clipping at 390 px width.
2. G50: random vs noise LFO behaviour (which is stepped vs continuous).
3. G57: what AUTO portamento really does (current guess: glide only on legato-style playing).
4. G58: PWM depth law in LFO/ENV mode (fader sets depth from a 50% base; spec does not say).
5. G62: 25% width on the 2-octave pulse sub position (owner judged it looks right from the panel).
6. G69: VCF bend range (1 octave at full), G70: VCO bend range.
7. LFO MOD switch on the bender (spec: "LFO MOD SW"). Not built.
8. Bender lever zones and hold behaviour on the physical panel. Not traced.
9. Unit-only checks (owner has the unit; not yet opened): TH1 thermistor (G6), far end of R100 (G8),
   MOD polarity through TR42 (G35), and the DC checks in `measurement_checklist.md`.
10. Python side: bring it up to date with the JS core, or retire it.

## Source documents (in the project)
- Roland SH-101 service manual scans (circuit diagram p.7, adjustment, parts list).
- Roland SH-101 technical specifications (support.roland.com, fetched).
- AS3109 datasheet (Alfa RPAR), V662A datasheet (coolaudio), CEM3340/3345 datasheet (Curtis).
- Secondary sources (use with care): AMSynths articles on IR3109 and BA662, Electric Druid AS3109
  schematic, Hackaday CEM3340 page, and photo-based observations of the owner's unit.

## Working conventions
- Every new parameter or behaviour gets a guess ID in `guess_ledger.md` with basis and confidence.
- Prefer the Roland spec and the owner's panel photo over secondary sources.
- Don't change the sound silently: if a change alters the default sound, say so and keep the
  previous render as a versioned WAV for comparison.
- The owner is the ear. Ask them to listen to changes before treating them as done.
