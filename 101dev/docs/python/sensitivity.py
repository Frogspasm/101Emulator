"""Which guesses change the audible or measurable result most? Each row perturbs one guess."""
import numpy as np
import sh101_vcf as m
import sh101_guessed as g

rows = []

# G5: VCA input load, effect on output level at 78% resonance, stage pole
def level_db(load, alpha=0.78, f=250.0):
    orig = list(m.PASSIVES)
    m.PASSIVES[:] = [(n,k,a,b,(load if n=="R_VCA_LOAD" else v),c) for (n,k,a,b,v,c) in orig]
    G,C,b = m.build(m.GM0, alpha, "ramp"); x = np.linalg.solve(G+2j*np.pi*f*C, b)
    G0,C0,b0 = m.build(m.GM0, 0.0, "ramp"); x0 = np.linalg.solve(G0+2j*np.pi*f*C0, b0)
    m.PASSIVES[:] = orig
    return 20*np.log10(abs(x[m.IDX["vca"]])/abs(x0[m.IDX["vca"]]))
rows.append(("G5 VCA load 1k vs 100k", "output level at 78% RES (dB)", level_db(1e3)-level_db(100e3)))

# G11: four-pole factor 0.435 +/- 0.03 -> pin 9 for 1 kHz (mV)
def pin9(k4):
    return -np.log2(1000/(k4*250.0))*0.019*1000
rows.append(("G11 four-pole factor +/-0.03", "cutoff error (octaves)", np.log2(0.465/0.405)))

# G6: thermistor 1k vs 2k (divider ratio) -> volts per octave at pin 9 for a fixed bus change
def vpo(r25):
    import sh101_vcf as mm
    ratio = mm.cv_divider(r_th_25=r25, B=3500.0, temp_c=25.0)
    return ratio
rows.append(("G6 TH1 1k vs 2k", "divider ratio (pin9/bus)", vpo(1000.0)-vpo(2000.0)))

# G13: keyboard gain +/-20% -> cutoff error at 3 octaves above C4 (Hz)
# tracking error in octaves: 20% more gain over 3 octaves of key = 0.2*3 octaves of cutoff error
rows.append(("G13 keyboard gain +20%", "cutoff error at C4+3 oct (octaves)", 0.2*3))

# G14: cutoff slider span (-1.0 V vs -0.5 V span) -> travel needed for 1 kHz at A4
g.CUT_BUS_MIN = -0.5
t_half = g.cutoff_slider_position(1000, (69-60)/12)
g.CUT_BUS_MIN = -1.0
t_full = g.cutoff_slider_position(1000, (69-60)/12)
rows.append(("G14 slider span 0.5 V vs 1 V", "travel for 1 kHz at A4 (fraction)", t_half-t_full))

# G1: reference symbol. DC only, no AC change in this model
rows.append(("G1 reference symbol", "DC bias only (no AC change)", 0.0))

print(f"{'guess':30s} {'output':38s} {'effect':>10s}")
for a,b,c in sorted(rows, key=lambda r: -abs(r[2])):
    print(f"{a:30s} {b:38s} {c:10.2f}")
