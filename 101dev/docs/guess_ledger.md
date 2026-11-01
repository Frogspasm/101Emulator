# Guess ledger: SH-101 VCF model

Every item here is an assumption made to finish the model. Each one should be checked against photos (foil side, component side, and close-ups of the marked nodes) or against a unit. The "photo to check" column says what would settle it.

| ID | Guess | Why we guessed | Effect if wrong | Photo to check |
|---|---|---|---|---|
| G1 | Dot-on-bar reference symbol = +5 V analog reference; hatched symbol = 0 V | Symbol shapes differ; errata and Electric Druid say "+5V not Gnd" for C1-C4 | Changes DC bias of all four stages, not AC response | Board-level photo showing where the +5 V trace goes near IC14 pin 1 |
| G2 | The 560 Ω input bus (R115/R116/R120/R123) returns to the same reference as G1 | No symbol drawn at the bus end; only C46's + terminal is nearby | DC only, if G1 holds | Foil-side photo of the bus pad near C46 |
| G3 | VR18 bottom end tied to +5 V, not ground | Errata list says VR18 is tied to +5 V instead of GND | Sets resonance DC offset; changes self-oscillation threshold | Close-up of VR18 solder pads |
| G4 | TR26 and TR27 are 2SC1815GR with hFE 250, and +15 V feeds the R135 / R136 network | Hfe from the parts list; +15 V from Electric Druid's drawing | Sensitivity of threshold is small (checked: 0.78–0.80 for hFE 100–400) | Transistor marking and the supply pad near R135 |
| G5 | VCA (IC15) input is loaded by about 1 kΩ to AC ground | IC15 input network not traced | Changes the resonance-dependent output gain: about +26 dB vs +37 dB at 78% resonance, between 100k and 1k loads | IC15 pin 1 and pin 2 resistors on the foil side |
| G6 | TH1 is a 1 kΩ NTC with B = 3500 K | SDT-1000 is a thermistor; R25 and B not in parts list | Sets divider tempco and the cutoff volts-per-octave | TH1 body marking; ohmmeter reading at room temperature |
| G7 | IC18b input mapping: R191 = MOD, R193 = ENV line, R189 = VR19 ENV amount | Lines cross near the summing node | Changes which slider has which gain | Top and left bus traces around IC18b pins 5–7 |
| G8 | VCO R101 (1.5M) and R105 (560) finish on pins 12 and 13 as drawn; VR6 end goes to pin 16 side | Small symbols; endpoints unclear | Changes VCO width and tracking | Foil side under IC13 pins 12–13 |
| G9 | TR24 terminal identity (collector top, emitter bottom, base to pin 4 node) | Small symbol, arrow direction hard to read | Changes PW bias and pulse-width range | TR24 orientation on component side |
| G10 | D30/D31 anti-parallel clamp between R113 and R129, returns to reference | Symbol orientation reads as anti-parallel | Only affects amplitude limiting; not in small-signal | D30/D31 orientation and their pad positions |
| G11 | 4-pole -3 dB point = 0.435 × single-stage pole (from the identical-stage model) | Uses identical stages; Roland's stages 2 and 4 have active loads, which may differ | Changes which VC gives 1 kHz by up to about 0.2 octave | Measured -3 dB point on the real unit |

Guess G5 is the most important, because it changes the output level by about 10 dB at high resonance. Guess G1 changes every DC operating point. Those two should be resolved first with photos.

## What the guesses predict (from the model)

- Calibration target: for a 1 kHz 4-pole -3 dB point at the A4 setting, pin 9 should read about −61 mV relative to pin 1. That needs about −0.55 V on the summed CV bus, using the 0.111 divider from G6. If the unit reads far from this, G6 or G11 is wrong, or the CUTOFF slider is not at the position the manual implies.
- G3 has no effect on the AC model, because the VR18 bottom end is at AC ground either way. It only changes DC bias, so it can be settled from DC readings alone.
- G5 controls the output-level prediction: about +26 dB (100k load) vs +37 dB (1k load) at 78% resonance, both measured at the stage pole.
- G4 changes the self-oscillation point by less than 0.02 of VR18 travel across the plausible gain range, so it is not a priority.

## Added while building the guessed model

| ID | Guess | Why | Effect if wrong | Photo to check |
|---|---|---|---|---|
| G12 | 8' is the 442 Hz reference; 16' is one octave down, 4' and 2' one and two octaves up | Service-manual tune reference; range data voltages 1–4 V step by octave | Shifts all pitch by whole octaves | Range switch S3 wiring and the range-data voltages on the VCO side |
| G13 | Keyboard tracking into the cutoff bus is set so one octave of KCV moves pin 9 by 19 mV (KYBD slider full) | Datasheet sensitivity; chosen so tracking is exact | Filter drifts against pitch if wrong | KYBD slider (VR21) wiring and summer gain |
| G14 | CUTOFF slider supplies a bus offset between 0 V and −1.0 V | Span not traced; chosen to be plausible | Changes slider position for 1 kHz, not the audio at that setting | VR17 end-to-end voltages |
| G15 | KCV zero sits at C4 on the cutoff path | Keyboard reference not traced | Shifts cutoff tracking by a fixed factor across the keyboard | KCV test voltages at known keys (service-manual test mode table) |

The tracking check in the code is true by construction, because G13 sets the gain. It confirms the arithmetic, not the hardware.

## Sensitivity ranking (sensitivity_results.txt)

Ranked by how much each guess changes a measurable or audible result:
1. G5, VCA input load: about 11 dB of output level at 78% resonance. Highest priority for photos.
2. G13, keyboard gain: each 20% error is about 0.6 octaves of cutoff error over three octaves of keyboard. High priority, because it changes how the filter tracks the keys.
3. G11, four-pole factor: each 0.03 error is about 0.2 octaves of cutoff error. Medium priority, and checkable with a sweep on the real unit.
4. G14, slider span: changes the slider position for 1 kHz but not the sound at that position. Low priority for audio.
5. G6, thermistor: changes the divider ratio by about 0.01, so it matters mostly for temperature drift. Low priority now.
6. G1, reference symbol: DC only. Low priority for audio, high priority for bias verification.

## New guess

| ID | Guess | Why | Effect if wrong | Photo to check |
|---|---|---|---|---|
| G16 | The summer is set so that keyboard CV raises the cutoff (positive key = brighter), as tracking requires | Sign of the inverting summer not traced | Filter would fall as you go up the keyboard | IC18b feedback and input polarity; a keyboard test on the unit |

## Pulse-width model (vco_pulse.py)

| ID | Guess | Why | Effect if wrong | Photo to check |
|---|---|---|---|---|
| G17 | PW pot (VR4) is linear: duty = 0.5 × wiper, spec range 50%..0% | Spec states 50%..0%; no law given | Pulse shape and PWM range shift, not pitch | VR4 taper marking and the wiring of R94/C37 |
| G18 | Envelope PWM depth: full envelope swing moves duty by up to 0.25 | PWM path (ENV/MAN switch) traced only partly | Changes how strongly the envelope pulses the sound | PWM switch and mixer resistors feeding pin 4/5 |

Correction recorded here: the service manual's 1:1 mark/space adjustment is done with VR-2 (D/A TUNE), not the PW pot, so it checks the D/A path. It is not a check of G17.

## CEM3340 external-network model (vco_cem3340.py)

The chip's internal ramp and comparator are not in the files, so they are parameters. The external network is read from the scan.

| ID | Guess | Why | Effect if wrong | Photo or check |
|---|---|---|---|---|
| G19 | PW comparator offset of 0.02 in duty units; wiper 0 gives about 2%, not the spec's 0% | Spec gives endpoints only | Changes the narrow-pulse end of the PW range | Measure duty at PW minimum on the unit |
| G20 | Chip's frequency vs control law is exactly 1 V/oct and the pulse duty is linear in the wiper | CEM3340 internal law not in the files | Tracking and pulse shape deviate by a few cents at the extremes | Tracking sweep on the unit at several keys (about 0.5 oct steps) |
| G21 | CEM3340 tempco: not available | Chip datasheet not uploaded | VCO drift with temperature is not modeled | Warm-up pitch drift on the unit; a CEM3340 datasheet would settle it |

Note on tracking: the zero tracking error in the model is by construction. It checks the arithmetic only. The real test is the unit.

## Confirmed-architecture update (secondary source: Hackaday CEM3340 module page)

Source is a hobbyist project page that follows the CEM3340 datasheet; the datasheet itself is linked there but was not available to fetch. Treat it as secondary.

| ID | Statement | Status | Effect | Photo or check |
|---|---|---|---|---|
| G22 | The CEM3340 frequency input (pin 15) is a current-summing virtual ground: each control voltage enters through a series resistor as V/R, and 1 V through 100 k is the reference. | Secondary-source support; consistent with R108 470k running from the VR7 wiper to the pin 15 node on the scan | Makes every tune and CV resistor a pitch gain of (100k / R) oct per volt | Trace R108 and the other pin 15 inputs on the foil side |
| G23 | The keyboard (KCV) enters pin 15 through a resistor giving about 1 oct/V (near 100 k), or a known fraction of it. Which resistor is unknown; R105 (560 Ω) cannot be the keyboard path because it would give 178 oct/V. | Open | Keyboard tracking of the whole VCO; a wrong resistor here moves pitch per key | Foil side at the pin 15 node; and a tracking sweep on the unit |
| G24 | Pin 9 of IC13 is grounded through about 100 nF if unused (datasheet practice cited in the Hackaday log) | Unverified | If pin 9 is floating on the Roland board, VCO noise may differ; no effect on the model | Foil side at IC13 pin 9 |
| G21 | CEM3340 tempco | Still not available. The Hackaday page does not give it. | Drift with temperature not modelled | Warm-up pitch drift on the unit; the datasheet would give it |

Suggested upload: the CEM3340 datasheet PDF. It would settle G20 and G21 directly, and it's the file the Hackaday page links to.

## Resolved by the CEM3340 datasheet (CEM3340-3345.pdf)

| ID | Was | Datasheet says | Status |
|---|---|---|---|
| G17 | PW wiper linear, duty 0.5 × wiper | PWM input 0 V = 0%, 5 V = 100% (typ), fits a linear law | Supported |
| G19 | Comparator offset 0.02 (guess) | PWM offset typ 0 V (±15 mV max) | Replaced by 0; the 0% endpoint is reachable |
| G20 | Chip law exactly 1 V/oct, duty linear | Exponential scale error 0.2% untrimmed, 0.05% trimmed: about 2.4 and 0.6 cents per octave of span. Trimming procedure given (R_Z / R_S / hi-freq track) | Quantified; trimmed error is small |
| G21 | CEM3340 tempco unknown | Oscillator drift typ ±50 ppm, max ±200 ppm; temperature-compensated internally | Resolved: VCO tempco is negligible. The filter's drift is the one that matters |
| G22 | Current summing, 1 V through 100 k = reference | Frequency control pin is a virtual-ground summing node; 100 k inputs give 1 V/oct | Confirmed by the datasheet |
| G27 | C41 1000 pF is the timing capacitor | Datasheet timing capacitor C_F: 1000 pF at Vcc = +15 V recommended for the 5 Hz–10 kHz range | Supported |

New checks from the datasheet:
- Frequency law: f = 3·I_EG / (2·Vcc·C_F). With C_F = 1000 pF, 442 Hz needs a reference current of 4.42 µA, which is inside the datasheet's recommended 3–15 µA. This supports the 1000 pF value and the reference-current architecture.
- Reference current pin is pin 13 (the datasheet's "linear FM" pin, with a 1.5 M resistor to +15 V in the application circuit). Roland's R101 (1.5 M) matches that. A 1.5 M resistor from +15 V gives 10 µA, which would read 1 kHz, not 442 Hz, so the 442 Hz tune must come from a different reference path or voltage. New guess G25.
- Pin 1 and pin 2 scale network: the datasheet's scale resistors (R_Z 24 k pot plus 10 k, and R_T 5.6 k) line up with the scan's R98 (28 k) and R97 (5.6 k). R97 = R_T is a good identification (moderate confidence on R98 as R_Z).
- Pin 4 (PWM control) has a 10 k series input in the datasheet's example, matching R95 10 k on the scan.
- Pin 7 is the high-frequency track trim. The Roland VR5 is labelled RANGE WIDTH on the scan, and the datasheet suggests it does the high-frequency scale trim. G26, moderate confidence.
- Negative control current behaves like zero. Raising frequency needs positive current, so VR7 (tune) can only raise the pitch from its reference. That is why the 442 Hz target sits on the reference side (G25).
- Pulse output is an open NPN emitter and needs a pull-down, which the Roland circuit should have. Not yet checked on the scan.

New guesses from this pass:

| ID | Guess | Why | Effect if wrong | Photo to check |
|---|---|---|---|---|
| G25 | The 442 Hz tune comes from the reference current at pin 13 (R101 1.5 M from a voltage below +15 V, or a different reference path). I_REF should be about 4.4 µA. | Datasheet says positive control current only raises the pitch; 1.5 M from +15 V alone gives 1 kHz | Sets the absolute pitch of the whole VCO | Trace R101's other end on the foil side |
| G26 | VR5 (RANGE WIDTH) is the datasheet's high-frequency track trim at pin 7 | Datasheet trim procedure, and VR5 sits next to the pin 7 network | Changes pitch above the mid-range, not the sound below | Trace VR5 to pin 7 on the foil side |

## G25 sharpened (reference_check.py)

- The 442 Hz tune needs I_REF ≈ 4.42 µA through R101 (1.5 M), which means the far end of R101 sits near 6.6 V.
- From +15 V it would give 1 kHz, and from +10 V about 667 Hz. Neither can reach 442 Hz at zero control current.
- G25 is now: R101's far end is a reference near 6.5–6.6 V (a zener-like node or a divider), with VR7 trimming the rest. Predicted pitch from a 6.5 V node is about 433 Hz, close to 442 Hz.
- Check: trace R101's other end on the foil side. A 6.5–6.8 V node there would confirm it; a +15 V or +10 V node would mean the tune path is different.

## Best estimates (all open items)

Confidence: high / medium / low. "Basis" is what the estimate rests on.

| ID | Item | Best estimate | Confidence | Basis |
|---|---|---|---|---|
| G5 | VCA input load | About 1 kΩ, so keep the 1 kΩ model value | Medium | The scan shows R138 1k and R139 1k at the IC15 input, close to the 1k model value |
| G25 | Tune reference node (R101 far end) | About 6.5–6.6 V | Low–medium | Only this voltage gives 442 Hz with R101 alone (reference_check.py) |
| G26 | VR5 (RANGE WIDTH) function | High-frequency track trim on CEM3340 pin 7 | Medium | Datasheet trim procedure; VR5 sits on the pin 7 network |
| G16 | Summer sign | Keyboard CV raises cutoff | High | Required for normal keyboard tracking; any other result would be unplayable |
| G13 | Keyboard gain into the cutoff bus | Set so one octave of key moves pin 9 by about 19 mV | Medium | Chosen to match the datasheet sensitivity; the keyboard resistor is not traced |
| G14 | CUTOFF slider span | 0 V to −1 V bus offset | Low | Plausible for a 1 V/oct-style slider; not traced |
| G7 | IC18b input mapping | MOD via R191, ENV line via R193, ENV amount via R189 | Medium | Lines cross near the summing node; the mapping is the most likely reading |
| G23 | Keyboard resistor into pin 15 | Unknown, but it must give about 1 oct/V (near 100 kΩ) | Low | Only a ~100 kΩ input can track 1 V/oct; no candidate traced yet |
| G6 | TH1 thermistor | About 1 kΩ at room temperature, B ≈ 3500 K | Low | Common SDT-type values; not measured |
| G1 | Reference symbol meaning | Dot-on-bar = +5 V reference, hatched = 0 V | Medium | Matches the errata wording ("+5V not Gnd") and the datasheet's supply pattern |

**What the estimates change**
- The VCA load estimate (about 1 kΩ) is the same as the model's value. That implies the high-resonance output boost of about 37 dB at the stage pole, which is the prediction to test first on the unit.
- Everything else leaves the sound unchanged. The open items mostly change absolute pitch (G25), the slider position for 1 kHz (G14), or tracking (G13, G23).

**Where to start on the unit or the photos:** G25 (R101's far end) is the one that would move the pitch the most, and it's a single pad to check.

## Keyboard path and VCA stage (keyboard_vca.py)

Confirmed from the service manual:
- KCV is 1 V per octave: lowest F (F3) = 0.417 V, highest C (C8) = 5.0 V. The difference (4.583 V) equals 55 semitones at 1 V/oct. Consistent.

| ID | Guess | Status | Effect if wrong | Check |
|---|---|---|---|---|
| G28 | BA662 VCA gain is linear in its control voltage | Unverified; BA662 datasheet not in the files | Envelope shape of the note changes; not pitch | BA662 datasheet, or an envelope-to-loudness sweep on the unit |
| G29 | KCV reaches VCO pin 15 through a resistor giving about 1.0 oct/V (the 100 k estimate, G23) | Estimate | If the keyboard resistor is different, the VCO tracks at a fixed wrong ratio | Keyboard tracking sweep on the unit (C3 to C5 scale) |
| G30 | Keyboard CV raises the cutoff (G16), with the keyboard term entering pin 9 negatively | Applied in code | Filter falls as you go up the keyboard if wrong | Cutoff sweep across keys on the unit |

Results from the model:
- KCV at A4 = 1.75 V, and the VCO at 8 ft gives 442 Hz there (the tune reference), by construction.
- Cutoff tracks the keyboard: C4 to A4 is 0.75 octaves, and the cutoff goes from 1000 Hz to 1681 Hz, as expected.
- The VCA-node level rises about 42 dB from zero to high resonance, consistent with the earlier output-level result (G5, 1 kΩ load). Absolute levels are arbitrary units; only the ratios matter here.
- `sh101_keyboard_scale.wav` plays a C3 to C4 scale through the tracked VCO, tracked cutoff, and gated VCA.

## BA662 article (amsynths, "All about the BA662 chip") applied to the VCA

Secondary source (manufacturer of clone modules), so treat with care. Relevant points:

| ID | Result | Status | Effect on the model |
|---|---|---|---|
| G28 | The article describes the BA662 as a DC-controlled variable transconductance amplifier, but does not give the control law (linear or exponential). | Still unresolved | Gain law of the VCA remains a guess (linear, as modelled). Test by a loudness sweep on the unit. |
| G31 | The scan's IC15 is marked BA662A. The article says the A version has lower offset and is used in VCA positions because offset causes a "thump". | Supported (high confidence) | Confirms the VCA part; the offset is a sound effect (gate on/off click), not modelled yet. |
| G32 | Gm matching is needed for filters (4 OTAs must match, or the filter won't self-oscillate below about 400 Hz) but not for a VCA. | Supported | The VCA needs no matching; the VCF does. Consistent with the model's single VCA stage. |
| G33 | Internal buffer mode: for a typical VCA the buffer is used (pin 4 to ground, pin 7 to pin 6). The article warns that a floating or grounded input on an unused buffer is a failure mode. | Unverified for the Roland board | No effect on the model; a possible cause of noise or thumps if the board's wiring differs. Check pins 4, 6, 7 on the foil side. |

Note: the article gives gm figures for the BA662 family (yellow dot gm = 8080; cloned BA6110 typical 8000; AS662 range 7700–9100), but no VCA gain or control law, so it does not settle G28.

## G28 resolved: VCA gain law (V662A datasheet, coolaudio, rev dated 2020/10/12)

- Datasheet formula: Av = gm·Ro = (I_CONTROL [mA] / 52 mV) × Ro. Gain is linear in control current.
- Datasheet states "good linearity... over three decades" (1 µA to 1 mA). Fig. 3 shows the open-loop gain against control current on a log axis, which is a straight line in dB, consistent with the linear law.
- The BA662A in the Roland VCA is the same kind of device (the article calls the V662 a clone of the BA662 architecture), so a linear control law is the best estimate. Confidence: medium-high. It is not proof for the original BA662.
- Model consequence: keep the linear gain (G28 closed). A 1 µA to 1 mA control range gives 60 dB, which the envelope's full swing would use.
- Note from the datasheet on the buffer (pin 4): bipolar supplies may connect pin 4 directly to ground, which supports the G33 wiring (pin 4 to ground) for the Roland board. Pin 8 needs an external load above 33 kΩ.
- Datasheet numbers: gm 4800 / 8000 / 12000 µS (min/typ/max) at 500 µA; max control current 650 µA; pin 6 output up to 500 µA typ; offset 3 mV max; residual noise −94 dBm (0 µA) and −74 dBm (200 µA).

Correction to the figures above: a units error in the first table gave gains 1000 times too large. Corrected values with Ro = 27 kΩ: 1 µA gives 0.52 (−5.7 dB), 10 µA gives 5.2 (14.3 dB), 100 µA gives 52 (34.3 dB), 500 µA gives 260 (48.3 dB), 1 mA gives 519 (54.3 dB). The range is 60 dB, as stated.

## Educated guess: G29 (keyboard resistor into pin 15)

- Guess: 100 kΩ (or a 100 kΩ-equivalent network), giving 1.0 oct/V. Confidence: medium.
- Why: (1) the keyboard span is 4.583 V over 55 semitones, which only tracks correctly at 1 oct/V; (2) 100 kΩ is the datasheet's 1 V/oct input value; (3) the other pin 15 input we traced (R108, 470 kΩ, the tune) is deliberately low-gain at 0.21 oct/V, so the keyboard must be the high-gain path.
- Consequence: keeps the current model (tracking gain 1.0 oct/V). If the photos show a different value, the keyboard range would be off by the same ratio.
- Check: a tracking sweep on the unit (C3 to C5 at a fixed filter setting), or the pin 15 foil-side trace.

## Answers found by re-reading the clean circuit diagram (service manual PDF, circuit diagram page, 7340 px wide)

The service manual PDF holds a sharper, un-annotated copy of the circuit diagram than the image first uploaded. Items below were read from it.

### Resolved or strongly supported

| ID | Result | Confidence | Evidence |
|---|---|---|---|
| G5 | VCA input load is 1 kΩ: C53 couples into IC15 pin 3, with R139 1k to the reference bus; R138 1k balances pin 2. Output load R140 47k on pin 6. | High | Clean diagram, IC15 crop |
| G4 | TR26/TR27 are 2SC1815GR (legend: "OTHER NPN TR: 2SC1815GR"; PNP are 2SA1015GR) | High | Parts legend |
| G10 | D30/D31 are an anti-parallel pair from the R113/R129 node to the reference | High | Clean diagram |
| G16/G30 | Keyboard and envelope raise the cutoff. IC18b is an inverting summer (R192 33k), and the IR3109 cutoff rises as pin 9 goes negative, so a positive control voltage gives a higher cutoff. | High | IC18b topology plus the datasheet sign |
| G24 | CEM3340 pin 9 is bypassed with C42 0.01 µF to ground, as the datasheet advises | High | Clean diagram |
| G27 | C41 1000 pF (silver mica) from pin 11 to ground, pin 12 grounded: this is the timing capacitor | High | Clean diagram plus datasheet |
| G1 | Dot-on-bar symbol is the +5 V analog reference. Extra support: IC15's buffer-bias pin 4 sits on that bus, which matches the V662A datasheet advice to bias the buffer near half the supply on a single rail. | Medium-high | IC15 crop; V662A datasheet |
| G7 | Cutoff summer inputs: ENV via VR19 → R189 100k; MOD via IC18a (a buffer on the VCF LFO/bend line) → VR20 → R191 100k; FREQ via VR17 → R186 200k (plus R187 680k and R184/R185 offsets); KYBD via VR21 and TR42 → R193 150k. Gains at the summer: 0.33, 0.33, 0.165 and 0.22 before the pot settings. | Medium-high (KYBD stage: low) | Control-board crops |
| G29 | The keyboard resistor is R104, 100 kΩ 1% (the errata list names R104 as the CV input). It gives 1 oct/V. | Medium-high | Scan plus errata |
| G12 | Range steps are one octave: R99 97.6 kΩ plus VR5 (0 to 5 kΩ) ≈ 100 kΩ, trimmed by VR5 "RANGE WIDTH" until a range step equals a key step (manual's adjustment C) | Medium-high | Scan plus manual |
| G26 | Corrected: VR5 is the range-channel scale trim, not the high-frequency track. VR6 (0–300 Ω) with R106 1.69k is the CEM3340's R_S scale trim at pin 14. The high-frequency-track position (pin 7) has R199 10k and an unfitted "VCO LINEAR" trimmer position (VR30, jumpered). | Medium-high | Scan, board silkscreen photo, datasheet |
| Scale | With R_Z = R98 28k, R_T = R97 5.6k and R_S = 1.69k + VR6, the datasheet formula gives 9.5–11.2 µA per octave across VR6's range. 10 µA per octave (1 V/oct through 100 kΩ) is reached at R_S ≈ 1.89 kΩ, inside the range. | High | reference_check.py |

### Corrections to my earlier statements

- **G25 (tune reference) was wrong.** I had treated the reference current as the zero-control-current frequency and concluded R101's far end sits near 6.6 V. The datasheet's law is the other way: zero control current gives the lowest frequency (about 0.6 Hz here), and the reference current sets the top of the scale. R101 (1.5 MΩ to the + rail) is the datasheet's reference resistor R_R, so f_ref = 3/(2·R_R·C_F) = 1 kHz regardless of rail voltage. A4 at 442 Hz then needs about 95 µA of total control current, set by the KCV, range, tune and fixed offsets. The "6.5 V" estimate is withdrawn.
- **G9 (TR24/TR25 roles) was wrong.** Pin 4 of the CEM3340 is the pulse output (the datasheet shows a pull-down there), so TR24 buffers the pulse output (R95 10k, R93 1k pull-down). Pin 5 is the PWM input, driven through R96 100k from TR25 and set by VR4 via R94. They are not a "steering pair". Terminal identity of TR24/TR25 is still not verified.
- **IC18a is the MOD buffer, not the KYBD buffer.** It sits on the VCF LFO/bend line with R188 47k to the reference.
- **The VR8 range check I started to describe used the wrong divider** (R188 was not in the keyboard path). VR8 (0–47k) is a series resistor ahead of VR21 (100k to ground), so it scales the keyboard path between about 0.68 and 1.0. The required tracking scale is about 0.78 of full path gain, which is inside that range only if TR42 acts as a unity buffer. TR42's role is unresolved.

### Still open

| ID | Item | Why |
|---|---|---|
| G25′ | Where the fixed offset current comes from. Illustrative budget (low confidence): KCV 27.5 µA + range 20 µA leaves about 48 µA; R103 (100k from IC12b, which rests near +5 V) would supply about 50 µA. R100 1.5M's far end is not traced. | Absolute pitch is set by the tune procedure anyway, so this barely affects the sound model |
| G13 | Exact keyboard path gain (TR42, VR21 and VR8 together) | TR42's role unclear |
| G14 | FREQ slider span (VR17, VCF cutoff; not the LFO RATE slider VR10) and the open-triangle symbol at VR17's top | Symbol meaning not confirmed |
| G6 | TH1 value and type (NTC or PTC) | Not on any file |
| G8 | R100 1.5M far end | Lower end runs off the traced area |
| G11 | Four-pole factor with active-load stages 2 and 4 | Needs unit measurement |

## Educated guess: TR42 and VR8 (keyboard path to cutoff)

| ID | Guess | Basis | Confidence |
|---|---|---|---|
| G34 | VR-8 (labelled VCF WIDTH) is the keyboard-tracking scale trim, not a filter width control. | Service manual VCF adjustment: "adjust VR-8 (VCF WIDTH) until the F5 figure cycle is twice the F4 cycle." That is exactly a 1 oct/oct tracking calibration. | Medium-high |
| G35 | TR42 is a MOD-path inverting stage with a 33 kΩ collector load (R195) feeding the KYBD slider VR21. It is not part of the tracking gain. | Scan: TR42 base from the VR20 (MOD) wiper, collector pulled up through R195 33k, output to VR21. Its gain sets the MOD polarity, not the tracking. | Medium |
| G13 (closed) | Keyboard tracking gain into the cutoff bus is fixed by the VR-8 adjustment, so it is set to exact 1 oct/oct at the calibrated setting. | Follows from G34; the 0.171 model gain is the calibrated value. | Medium-high |

Consequence for the model: the keyboard tracking is exact (1.0 oct/oct) by calibration, so the only remaining cutoff unknown is the FREQ slider span (VR17, VCF cutoff; not the LFO RATE slider VR10) (G14). Earlier wording that VR8 is "a series resistor ahead of VR21" is withdrawn.

## G14 closed by the service-manual spec: VCF cutoff 10 Hz to 20 kHz

- The spec sets the cutoff range at 10 Hz to 20 kHz, about 11 octaves. My earlier guess (a 1 V span) covered only about 5.8 octaves, so it was too narrow.
- Using the datasheet sensitivity (19 mV per octave) and the 0.111 divider, the slider needs a bus span of 1.877 V: +0.589 V at 10 Hz (bottom), −1.288 V at 20 kHz (top).
- A 1 kHz cutoff at C4 sits at 0.61 of travel, not 0.32 as before.
- Effect on the emulator: the same panel positions now give different cutoffs. The approved demo clip was rendered with the old mapping, so re-rendering it will sound different. The demo file in the folder is the earlier render.
- Confidence: high for the range (it's the spec), medium for the linear-in-volts slider law.

Demo files after the G14 change:
- `sh101_emulator_demo_v1.wav`: the clip you approved, rendered with the old 1 V slider span.
- `sh101_emulator_demo_v2.wav`: the same patches with the spec's 10 Hz to 20 kHz span. Patch cutoffs now land lower, so it sounds darker. Compare the two.

## Performance features (phone page, sh101_core.js)

| ID | Item | Basis | Confidence |
|---|---|---|---|
| G45 | Arpeggio steps are sixteenth notes; gate is 60% of a step; modes up, down, up/down | Manual's test table names up, down and up&down arpeggio modes; step length and gate are guesses | Medium |
| G46 | Transpose: L = 0, M = +12 semitones, H = +24 semitones | Manual's test-mode KCV table: M raises the lowest F by 1 V (one octave), H by 2 V | High |
| G47 | Portamento is exponential glide over 0 to 5 s (service-manual range); time constant = time / 3 | Range from the manual's spec; curve shape is a convention | Medium |
| G48 | Legato: a new key while another is held changes pitch without restarting the envelopes | Standard analog behaviour; the manual's legato mode is not traced | Medium |
| G49 | Bender: pitch range ±2 semitones, springs back to centre on release; mod wheel sets vibrato | Bender range is a convention; mod is the MOD lever | Medium |

## Switches (phone page, sh101_core.js)

| ID | Switch | Basis | Confidence |
|---|---|---|---|
| G50 | LFO waveform: square, triangle, noise (continuous random), random (sample-and-hold, new level each cycle). The four settings are confirmed on the panel: triangle, square, random, noise. | Panel confirmed by the user; which of random and noise is held vs continuous is still a guess | Medium (positions confirmed) |
| G51 | VCO wave: saw, pulse, or both. The switch gates the saw and pulse mixer levels; the sliders set the levels. | Service-manual block diagram shows saw and pulse into the source mixer; the switch positions are a convention | Medium |
| G52 | Sub: off, 1 octave down, or 2 octaves down (square). | Manual's block diagram labels 1 OCT DOWN and 2 OCT DOWN | High for positions, medium for waveform |
| G53 | VCA: ENV (envelope controls loudness) or GATE (loudness follows the key). | Scan switch S6 has ENV and GATE positions | Medium-high |
| G54 | Envelope trigger: GATE (note-on restarts the envelope, legato respected), GATE + TRIG (every note restarts it), LFO (envelope restarts on each LFO cycle and ignores keys). | Scan switch S6 labels GATE, GATE + TRIG and LFO | Medium |
| G55 | Hold: notes released while hold is on keep sounding; turning hold off releases any key no longer held. | Standard latch behaviour; the manual's hold function is not traced | Medium-high |

## PWM source and portamento mode (panel switches)

| ID | Item | Basis | Confidence |
|---|---|---|---|
| G56 | PWM source switch: ENV (envelope moves the width, as before), LFO (LFO moves the width, same depth), MAN (fixed width, pulse-width slider only). | Panel labels LFO, MAN, ENV beside the pulse-width slider | High for positions, medium for the LFO depth |
| G57 | Portamento mode: ON glides every note, OFF never glides, AUTO glides only when a key is played while another is held. | Panel labels AUTO, OFF, ON; the AUTO meaning is inferred, not from a manual | Medium |

## Checked against the Roland SH-101 technical specifications (support.roland.com)

The Roland spec is the primary source for these items. It corrects some earlier guesses.

| ID | Item | Result |
|---|---|---|
| G51 (corrected) | VCO wave switch | Not a Roland control. The spec lists separate Square/Pulse and Sawtooth level knobs in the Source Mixer, so the VCO wave switch was removed from the page. |
| G58 | PWM | The spec lists one "Pulse Width Modulation" knob (50% to min.) and a PWM mode switch (ENV / MANUAL / LFO), with no separate depth control. The page now uses the one fader: in MAN it sets the width, in LFO and ENV it sets the depth from a 50% base. Confirmed for the mode switch and range; the exact depth law is still a guess. |
| G61 | Key Follow | Spec: VCF Key Follow knob, 0 to 100%. Added as a slider; 0 gives no keyboard tracking. |
| G62 | Sub oscillator | Spec calls this a SUB OSC waveform selector switch. The page still uses off / 1 oct / 2 oct; the panel labels read 1 OCT DOWN and 2 OCT DOWN. Whether an "off" position exists and what the waveforms are is still open. |
| G63 | Bender | Spec has separate VCO Bend Sens and VCF Bend Sens knobs, plus a bender lever with an LFO MOD switch. The page applies the bender to pitch only. The VCF bend is not built yet. |
| G64 | LFO wave | Spec: Modulator Waveform selector switch. Confirms a switch rather than a knob; the four settings (triangle, square, random, noise) are the panel labels. |
| G65 | Arp and gate | Spec: arpeggio UP, U&D, DOWN; ENV/GATE switch on the VCA; GATE + TRIG / GATE / LFO trigger switch. These match the page. |

## Sub oscillator (confirmed from the panel photo)

The panel's SUB OSC switch has three positions, as the user reads it: 1 OCT DOWN square, 2 OCT DOWN square, 2 OCT DOWN pulse. There is no "off" position, so the page's off setting was removed.

| ID | Item | Basis | Confidence |
|---|---|---|---|
| G62 | The 2 OCT pulse position is a pulse at 25% width. | Panel photo shows a pulse icon; width is not printed. User judged 25% to look right from the panel. | Medium (width judged visually) |

## Rotary knobs (photo: TUNE, WAVE FORM, RANGE, VOLUME, PORTAMENTO)

The knobs use the same drag-to-turn control in every case. Each one drives a hidden control, so the patch code is unchanged. The AcidBox knob code wasn't available in this environment, so the knob is a new build in the same style. If you upload the AcidBox knob, I'll swap it in.

| ID | Item | Basis | Confidence |
|---|---|---|---|
| G66 | TUNE knob: ±50 cents, centred at 442 Hz | Spec: "Tune knob (+50 cent)" | High |
| G67 | RANGE and WAVE FORM knobs step through their positions (16', 8', 4', 2'; triangle, square, random, noise) | Panel photo | High |
| G68 | VOLUME and PORTAMENTO are continuous knobs (portamento 0 to 5 s) | Panel photo; spec range | High |

## Bender sensitivity (VCO Bend and VCF Bend sliders)

The photo shows VCO and VCF as vertical sliders in the controller section, so both are sliders.

| ID | Item | Basis | Confidence |
|---|---|---|---|
| G69 | VCF bend: full lever moves the cutoff by ±1 octave at full VCF Bend | Spec names a VCF Bend Sens control; the one-octave range is a guess | Low (range), high (existence) |
| G70 | VCO bend: full lever moves pitch by ±2 semitones at full VCO Bend | Same ±2-semitone range as the earlier pitch bend; scaled by the VCO Bend slider | Medium |

## Layout follows the panel photo

The page is grouped as on the panel: TUNE; Arpeggio, Legato and Transpose; Modulator (LFO/CLK rate, WAVE FORM); VCO (MOD, RANGE, PULSE WIDTH with PWM source); Source Mixer (square/pulse, saw, sub with its switch, noise); VCF (FREQ, RES, ENV, MOD, KYBD); VCA; ENV (gate switch, A, D, S, R); Controller (VOLUME, PORTAMENTO, portamento mode, bend sliders, LFO MOD, bender).

The LFO/CLK rate slider (0.1 to 30 Hz, exponential) and the VCF MOD slider were added to match the panel. No new sound parameters were introduced.
