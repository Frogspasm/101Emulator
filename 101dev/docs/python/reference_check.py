"""
CEM3340 frequency law, applied to the external network read from the Roland scan.
(Replaces the earlier version, which treated the reference current as the zero-control-current
frequency. That was a misreading of the datasheet.)

Datasheet (CEM3340-3345.pdf, pp.3-4):
  I_OM = (22 V_T / R_T) (1 - I_C R_Z / 3.0)      multiplier output current
  V_B  = I_OM * R_S                               base voltage of Q1
  I_EG = I_REF * exp(-V_B / V_T)                  exponential generator current
  f    = 3 I_EG / (2 Vcc C_F)
Zero control current gives the LOWEST frequency; I_C = 3.0/R_Z (V_B = 0) gives f = 3 I_REF/(2 Vcc C_F).

Roland values read from the scan (clean copy, PDF p.9):
  R_Z = R98 28k (pin 1), R_T = R97 5.6k (pin 2), R_S = R106 1.69k + VR6 (0..300 ohm) (pin 14),
  R_R = R101 1.5M to the + rail (pin 13), C_F = C41 1000 pF (pin 11, pin 12 grounded).
"""
import numpy as np
VT, RT, RZ, CF, RR = 0.02585, 5.6e3, 28e3, 1000e-12, 1.5e6

f_ref = 3.0 / (2 * RR * CF)        # I_REF = Vcc/R_R, so Vcc cancels
I_full = 3.0 / RZ                  # control current at which f = f_ref
print(f"reference frequency f_ref = {f_ref:.0f} Hz (independent of the supply rail)")
print(f"control current for f_ref: {I_full*1e6:.1f} uA")

def i_per_octave(RS):
    return np.log(2) * RT * 3.0 / (22 * RS * RZ)

print("\nScale trim (VR6 adds 0..300 ohm to R106 1.69k at pin 14):")
for RS in (1.69e3, 1.84e3, 1.89e3, 1.99e3):
    print(f"  R_S = {RS/1e3:.2f}k -> {i_per_octave(RS)*1e6:5.2f} uA per octave")
print("  1 V/oct through 100 k = 10.00 uA per octave -> reached at R_S about 1.89k, inside the VR6 range.")

RS = 1.89e3
VB0 = 22 * VT * RS / RT
def ic_for(f):
    vb = -VT * np.log(f / f_ref)
    return (1 - vb / VB0) * I_full
print(f"\nControl current needed for 442 Hz (R_S = {RS/1e3:.2f}k): {ic_for(442.0)*1e6:.1f} uA")
print(f"Lowest frequency at zero control current: {f_ref*np.exp(-VB0/VT):.2f} Hz")

print("\nIllustrative budget at A4, 8 ft, M transpose (LOW confidence, inputs partly inferred):")
kcv = 2.75 / 100e3
rng = 2.0 / 100e3
need = ic_for(442.0)
print(f"  KCV 2.75 V via R104 100k: {kcv*1e6:.1f} uA   Range 2.0 V via R99+VR5 (about 100k): {rng*1e6:.1f} uA")
print(f"  Remaining current to find from fixed offsets and tune: {(need-kcv-rng)*1e6:.1f} uA")
print(f"  If R103 (100k from IC12b, resting near +5 V) supplied 50 uA, the remainder is {(need-kcv-rng-50e-6)*1e6:+.1f} uA,")
print("  which the VR7/R108 tune path (negative current only) could absorb. This is an inference, not a measurement.")
