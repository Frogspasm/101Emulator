"""
Starting model of the SH-101 four-pole VCF (IR3109 / AS3109 class).

Built only from numbers in the AS3109 datasheet (Alfa RPAR, v2.2) and the
Roland SH-101 service manual adjustment section. Everything marked TODO is
not yet confirmed against the Roland board.

Model: four cascaded first-order OTA-RC low-pass stages with an exponential
control law, plus a linear resonance feedback term. This is a behavioral
starting point, not a transistor-level model.
"""
import numpy as np

# ---- Datasheet values (AS3109) ----
FC_AT_VC0 = 250.0          # Hz, single-stage -3 dB point at VC = 0
SENS_MV_PER_OCT = -19.0    # mV per octave (typical); range -17.5 .. -20.5
TEMPCO_PCT_PER_C = 0.33    # %/degC frequency tempco
FREQ_ERR_PCT_TYP = 4.0     # % typical frequency control error

def stage_cutoff(vc_volts, temp_c=25.0):
    """Single-stage cutoff vs control voltage (exponential law)."""
    octaves = (vc_volts * 1000.0) / SENS_MV_PER_OCT     # positive VC -> lower f
    f = FC_AT_VC0 * 2.0 ** (-octaves)
    f *= 1.0 + TEMPCO_PCT_PER_C / 100.0 * (temp_c - 25.0)
    return f

def ladder_response(freqs, fc, k, n_stages=4):
    """
    Frequency response of an n-stage cascade of identical first-order
    low-pass sections with resonance feedback gain k (0 .. 4).
    k = 0 gives a plain cascade; the feedback term is a linear approximation
    (no Q compensation, matching the SH-101 wiring described in the article).
    """
    s = 1j * 2 * np.pi * freqs
    wc = 2 * np.pi * fc
    g = (wc / (s + wc)) ** n_stages               # open-loop cascade
    h = g / (1.0 + k * g)                          # linear feedback around the ladder
    return h

def db(h):
    return 20 * np.log10(np.maximum(np.abs(h), 1e-12))

if __name__ == "__main__":
    print("Single-stage cutoff vs VC (datasheet check):")
    for vc in [-0.140, 0.0, 0.160]:
        print(f"  VC = {vc*1000:+6.0f} mV  ->  {stage_cutoff(vc):9.2f} Hz")
    octaves_span = (0.160 - (-0.140)) * 1000 / abs(SENS_MV_PER_OCT)
    print(f"  Span over datasheet control range: {octaves_span:.1f} octaves (datasheet says >= 15)")

    print("\nFour-pole cascade, VC = 0, k = 0:")
    f = np.logspace(1, 4.5, 2000)
    h = ladder_response(f, FC_AT_VC0, k=0.0)
    mag = db(h)
    f3_idx = np.argmin(np.abs(mag + 3.0))
    print(f"  -3 dB point: {f[f3_idx]:.1f} Hz (single stage was {FC_AT_VC0} Hz)")
    fa = f[np.argmin(np.abs(f - 2 * FC_AT_VC0))]
    fb = f[np.argmin(np.abs(f - 4 * FC_AT_VC0))]
    slope = (db(ladder_response(np.array([fb]), FC_AT_VC0, 0.0))[0]
             - db(ladder_response(np.array([fa]), FC_AT_VC0, 0.0))[0]) / np.log2(fb / fa)
    print(f"  Slope well above cutoff: {slope:.1f} dB/octave (expect about -24)")

    print("\nResonance sweep (k), VC = 0. Linear model: k >= 4 is unstable (self-oscillation not modeled):")
    for k in [0.0, 1.0, 2.0, 3.0, 3.9]:
        h = ladder_response(f, FC_AT_VC0, k)
        dc = db(ladder_response(np.array([1.0]), FC_AT_VC0, k))[0]
        print(f"  k = {k:3.1f}  peak above DC gain = {db(h).max() - dc:6.2f} dB")

    print("\nSuperseded: see sh101_vcf.py (component-level model using the transcribed Roland network).")
