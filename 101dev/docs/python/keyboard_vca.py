"""
Keyboard path and VCA stage, using the service-manual test values and the scan.

Keyboard path (service manual, CPU section and test-mode table):
  * KCV is 1 V per octave.
  * Lowest F (F3, MIDI 53) = 0.417 V at L transpose; highest C (C8, MIDI 108) = 5.0 V.
  Both are service-manual numbers. Their difference (4.583 V) should equal 55 semitones / 12.
  That is a consistency check on the 1 V/oct law, not an assumption.
  * KCV reaches the VCO pitch input through a resistor (G23 estimate: about 100 k -> 1.0 oct/V).
  * KCV reaches the cutoff bus through the KYBD slider VR21 (G13 estimate: gain set so one
    octave moves pin 9 by about 19 mV).

VCA stage:
  * IC15 (BA662) is the VCA. Its input is the VCF output via R130/R132 with a 1 k load (G5 estimate:
    R138 and R139 both 1 k on the scan).
  * Control: ENV or GATE, chosen by switch S6 (scan: ENV and GATE positions).
  * Gain law: linear in the control voltage (G28, unverified; BA662 datasheet not in the files).
"""
import numpy as np
from scipy.io import wavfile
from sh101_guessed import FS, vco_hz, envelope, ladder, PIN9_PER_BUS, KYB_GAIN, VC_OCT

# ---------------- keyboard ----------------
F3_MIDI = 53
KCV_LOWEST_F = 0.417          # service manual, L transpose
KCV_HIGHEST_C = 5.0           # service manual, highest C

def kcv(midi):
    return KCV_LOWEST_F + (midi - F3_MIDI)/12.0

def consistency():
    span_sm = KCV_HIGHEST_C - KCV_LOWEST_F
    span_law = (108 - F3_MIDI)/12.0
    return span_sm, span_law

# ---------------- VCO pitch from KCV (G23 estimate: 100 k gives 1.0 oct/V) ----------------
R_KCV_EST = 100e3
def vco_pitch_from_kcv(midi, rng="8"):
    gain = 100e3/R_KCV_EST          # octaves per volt into pin 15
    # reference: A4 = 442 Hz at 8 ft, which sits at KCV(A4)
    k_a4 = kcv(69)
    return 442.0*2**(gain*(kcv(midi)-k_a4))*2**({"16":-1,"8":0,"4":1,"2":2}[rng])

# ---------------- cutoff tracking from KCV (G13 estimate) ----------------
def pin9_from_kcv(midi, slider_bus=0.0):
    # G16: keyboard CV raises cutoff. Pin 9 volts fall as cutoff rises (datasheet sign),
    # so the keyboard term enters pin 9 with a negative sign.
    bus = slider_bus - KYB_GAIN*(kcv(midi)-kcv(60))     # reference at C4
    return PIN9_PER_BUS*bus

def cutoff_hz(midi, slider_bus):
    v9 = pin9_from_kcv(midi, slider_bus)
    return 250.0*0.435*2**(-v9/VC_OCT)

# ---------------- VCA ----------------
def vca_gain(control):
    return np.clip(control, 0.0, 1.0)     # G28: linear law

def vca_levels(alpha):
    """VCA-node level at the stage pole for a given resonance, from the component model (G5 load)."""
    import sh101_vcf as m
    G,C,b = m.build(m.GM0, alpha, "ramp")
    x = np.linalg.solve(G+2j*np.pi*250.0*C, b)
    return abs(x[m.IDX["vca"]])

if __name__ == "__main__":
    span_sm, span_law = consistency()
    print("== Keyboard KCV ==")
    print(f"  service manual span F3..C8: {span_sm:.3f} V; 1 V/oct law over 55 semitones: {span_law:.3f} V  -> consistent" if abs(span_sm-span_law)<0.01 else f"  MISMATCH {span_sm:.3f} vs {span_law:.3f}")
    print(f"  KCV at A4 = {kcv(69):.3f} V (service-manual-consistent)")
    for m_ in [53, 60, 69, 81, 108]:
        print(f"  MIDI {m_:3d}: KCV {kcv(m_):.3f} V, VCO {vco_pitch_from_kcv(m_):9.2f} Hz (8 ft)")
    print("== Cutoff tracking (slider at 1 kHz for C4 by construction) ==")
    v9_target = -np.log2(1000/(0.435*250.0))*VC_OCT          # pin 9 for 1 kHz (-61 mV)
    slider = v9_target/PIN9_PER_BUS                           # bus offset giving 1 kHz at C4
    for m_ in [53, 60, 69, 81]:
        print(f"  MIDI {m_:3d}: cutoff {cutoff_hz(m_, slider):8.1f} Hz")
    print("== VCA ==")
    for a in [0.0, 0.5, 0.78]:
        print(f"  resonance {a:.2f}: VCA-node level {vca_levels(a):.5f} (1 k load, G5)")

    # Preview: scale C3..C5 through the full chain: KCV-tracked VCO, KCV-tracked cutoff, linear VCA with gate
    notes = [48,50,52,53,55,57,59,60,62,64,65,67]
    pieces=[]
    for i,n in enumerate(notes):
        dur=0.22; rel=0.15; N=int((dur+rel)*FS)
        f = vco_pitch_from_kcv(n)
        ph = np.cumsum(np.full(N, f/FS)) % 1.0
        dt=f/FS
        from vco_pulse import polyblep
        osc = 2*ph-1-polyblep(ph,dt)
        cut = cutoff_hz(n, slider)
        env = envelope(N, 0.003, 0.12, 0.6, rel, dur)
        gate = vca_gain(env)                    # ENV position of S6 (G28 linear)
        pieces.append(ladder(osc*0.6, cut*np.ones(N), 1.2)*gate)
    a=np.concatenate(pieces); a=a/(np.max(np.abs(a))+1e-9)*0.8
    wavfile.write("sh101_keyboard_scale.wav", FS, (a*32767).astype(np.int16))
    print(f"wrote sh101_keyboard_scale.wav ({len(a)/FS:.1f} s): C3-C4 scale, tracked pitch and cutoff")
