# SH-101 VCF: what the uploaded material already answers

Correction first: the page 7 scan is readable at native resolution. My earlier statements that I could not read IC14's pins came from looking at it at full-page size. Cropped, it resolves most of the open items.

## Resolved

| Open item | Answer | Evidence |
|---|---|---|
| IC14 pin wiring on the Roland board | Same as the AS3109 datasheet: In/C/Out = 2/3/4, 5/6/7, 10/11/12, 13/14/15; VC = 9; GND = 1; VEE = 8; VCC = 16 | Scan p.7 crop; datasheet pin table |
| Stage 3/4 direction conflict | Roland board agrees with the datasheet (In3 = 10, Out3 = 12, In4 = 13, Out4 = 15). The block diagram image with pins 10-15 reversed is the odd one out | Resistor chain R119/R121/R124/R122 |
| Resistor values around IC14 | Seven 68k (R114, R117, R118, R119, R121, R124, R122); four 560 (R115, R116, R120, R123) | Scan |
| Integrator caps | C48 (pin 3), C47 (pin 6), C50 (pin 11), C51 (pin 14), all 240 pF | Scan |
| Capacitor return | They return to the pin-1 reference net, drawn with a dot-on-bar symbol. Pin 8 and C46 use the hatched ground symbol. The Electric Druid Rev.2 note ("to +5V, not Gnd") and the datasheet figure describe the same node, so there is no conflict | Zoomed symbols; errata wording |
| Resonance path | VCF out (pin 15) -> VR18 100kB -> TR26 (CE stage, R131 10k) -> TR27 follower (R137 33k) -> C52 -> R129 5.6k -> R113 15k -> pin 2 node, with D30/D31 clamp between R113 and R129 | Scan; maps one-to-one onto Electric Druid TR2/TR3 |
| Output mix to VCA | R130 150k from pin 15 and R132 150k from TR26 emitter, then C53 to IC15 | Scan |
| Source mixer values | R109 150k, R110 680k, R111 470k, R112 820k into C45 (10u BP) | Scan; names from Electric Druid |
| Red marks on the scan | They are the errata annotations (VR15, VR18, R137, R143 and so on) | Matches the errata list |
| Why 250 Hz at 240 pF / 68k | Not an RC product. Stage pole = gm x (1/123.4) / (2 pi C), because the 560 ohm shunt makes a 1:123 attenuator at each In node. That gives gm0 = 46.5 uS at VC = 0 | Derived |
| Thermistor | TH1 (SDT-1000) sits in the pin-9 CV divider with R128 4.7k, R126 1.8k, R127 5.6k, R125 820 | Scan |

## Model results (sh101_vcf.py, component-level, small-signal)

- Passband gain from each source equals 68k / R_source (noise 0.45, ramp 0.14, pulse 0.10, sub 0.08). Stage 1 is an inverting summing stage.
- Four-pole response: -3 dB near 111 Hz when each stage pole is 250 Hz; -24 dB/octave.
- Self-oscillation begins near 78% of VR18 travel (oscillates at the stage pole frequency).
- Output level vs resonance, measured at the stage pole (250 Hz). This replaces an earlier claim that the output mix "compensates" the level. That earlier number was a voltage-ratio metric that could not depend on the VCA load, so it tested nothing. At 78% of VR18, the VCF output is about +37 dB above its minimum-resonance level with a 1k VCA load and about +26 dB with a 100k load. The VCA node adds about 5 dB more than the VCF output at moderate resonance. So the output mix contributes resonance-dependent gain, and its size depends on the VCA input load. This is a testable prediction (see checklist). Note that the linear model's peak height near self-oscillation is not reliable, and the 1k load is the assumed value.
- The CV divider ratio is about 0.11 (if TH1 is 1k), so the cutoff CV bus needs roughly 170 mV per octave.
- If TH1 is an NTC of about 1k, the divider tempco is +0.20 to +0.27 %/degC against the chip's 0.33 %/degC. That would cancel most of the chip's drift.

## Assumptions in the model (check these first)

1. Dot-on-bar symbol = +5 V analog reference, hatched = 0 V. Strong inference, not measured.
2. The 560 ohm bus (R115/R116/R120/R123) is tied to the same reference. The drawing shows no symbol for it, only C46's + terminal.
3. TR26/TR27: hFE 250, DC bias estimated with pot wiper at the reference and a +15 V rail (from Electric Druid; Roland's drawing only shows an arrow).
4. VCA input loaded by 1k to AC ground. IC15's input network is not traced yet.
5. D30/D31 omitted in small signal. They set the self-oscillation amplitude and need a nonlinear model.
6. TH1 R25 and curve unknown.
7. OTA is linear. The real chip's input stage compresses at larger swings.

## Still open (needs the unit or another source)

- Summed cutoff CV: IC18 and the FREQ/ENV/MOD/KYBD sliders are legible but not transcribed.
- IC15 (BA662) VCA and the envelope section.
- Supply voltages at pins 1, 8, 16 and the +15 V rail.
- TH1 resistance versus temperature.
- Real self-oscillation threshold, to check the 78% prediction.
- The VCO (CEM3340) network is also legible in the same scan and can be transcribed next.

## VCO (IC13, CEM3340), partial transcription

Read with confidence at native resolution (pin numbers are the CEM3340 pins on the scan):
- Pin 1 via R98 28k and pin 2 via R97 5.6k to one node, which has C39 2.2 uF/50 V to ground. This is the ramp-timing network for the sawtooth.
- Pin 4 via R95 10k from the TR24 emitter node, which has R93 1k to ground.
- (Corrected) TR24 buffers the pulse output at pin 4 (R95 10k, R93 1k pull-down). TR25 drives the PWM input at pin 5 through R96 100k; VR4 (PW, 50 kB) with R94 100k and C37 0.01 uF sets the manual width.
- R96 100k from the TR25 emitter node to the pin 5 node.
- Pin 6 with C38 0.01 uF to ground.
- Pin 7 via R99 (scan label R199, one of the errata-corrected parts) to ground, and the pin 7 node also goes to the 100k VR5 range-width path.
- Pin 8 to ground.
- Pins 13, 14: R105 560 from the pin 13 node, R106 1.69k from pin 14 to ground, R101 1.5M, and VR6 (VCO width, 300 B) feeding through R108 470k.
- Pins 9, 11: C42 and C41 (1000 pF, switched) and C43 0.01 uF on the frequency-capacitor side.
- Pin 15 is supply-side, with C40 2.2 uF to pin 16.
- R115 to R124 (the 560 / 68k chain) are the IC14 network already transcribed above.

Second pass (higher zoom), with confidence noted:
- TR24: top terminal to +5 V through R92 68k; bottom terminal to ground; control terminal at the pin 4 node, which carries R95 10k to pin 4 and R93 1k to ground. Moderate confidence on terminal identity, because the symbol is small.
- VR7 (VCO TUNE, 100 kB): one end to ground, wiper through R108 470k to the pin 15 node. High confidence.
- VR6 (VCO WIDTH, 300 B trimmer) feeds the width bus; the far end goes toward pin 16 via C40 2.2 uF/50 V. Moderate confidence.
- VR31 (VCF TUNE) is on the VCF side, not in the VCO network.
- (Corrected) VR5 is the range-channel scale trim (R99 97.6k + VR5 ~ 100k), and VR6 + R106 1.69k is the CEM3340 R_S scale trim at pin 14. See guess_ledger.md.
- Still open: the R101 1.5M and R105 560 finishing nodes on pins 12-13, and whether R106 1.69k finishes on ground or on VR6. Treat the VCO netlist as partial until these are checked.

Note on the VR4 "PW" circuit: the pulse-width trimmer sets the duty ratio. The service manual's adjustment is 1:1 mark/space at the 2 pole setting, which gives a check.

## Cutoff CV summing (control board, IC18), read at high zoom

- (Corrected) IC18a is a unity-gain buffer on the VCF LFO/bend line (R188 47k to the reference on pin 3); its output feeds the MOD slider VR20.
- IC18b is an inverting summing amplifier: pin 6 (inverting) takes the summed inputs and has feedback R192 33k from pin 7. Inputs are R193 150k (from the ENV line), R191 100k (from the MOD line), and R189 100k from the VR19 (ENV amount) wiper. Output pin 7 is the summed cutoff CV that feeds the VCF bus. Moderate confidence on which input is which, because the lines cross near the node.
- VR17 (FREQ), VR18 (RES), VR19 (ENV), VR20 (MOD), VR21 (KYBD), VR16 (NOISE) are identified by their silkscreen labels above each slider. High confidence on the labels, moderate on the exact KYBD path.
- IC17 (4013) is the sub-octave flip-flop circuit, not part of the cutoff summing.

What this does not yet give us: the absolute mapping from panel and keyboard to the VCF control voltage. The VCF divider (R125 820 to reference, R128 4.7k, the R126/R127/TH1 network) and the IC18b gain together set the volts per octave at pin 9. The model estimated about 170 mV per octave with TH1 at 1k, which is still an estimate.

Next steps for the summing path: confirm the R189/R191/R193 inputs by tracing the top and left bus lines, then compute the 1 kHz point at A4 from the summed gain and check it against the service-manual calibration.
