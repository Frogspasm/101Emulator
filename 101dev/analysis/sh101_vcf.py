"""
SH-101 VCF (IC14 = IR3109) - component-level small-signal model.

Netlist transcribed from the Roland service-manual circuit diagram (p.7, Nov 1982),
cross-checked against the AS3109 datasheet (Fig. 3) and the Electric Druid
"AS3109 SH-101 Filter" Rev.2 schematic. Every value below is read off the scan;
see FINDINGS.md for what is confirmed vs assumed.

Small-signal conventions:
  * 0 V rail, +5 V analog reference (pin 1 net) and the decoupled supplies are all AC ground.
  * Each OTA is a transconductance gm into its cap node; each buffer is ideal unity.
  * OTA input is the inverting input (block diagram: IN -> "-"), which is the only
    sign that gives stable negative feedback through the 68k/68k node.
  * D30/D31 clamp is treated as open in small signal (it limits amplitude only).
"""
import json
import numpy as np
from scipy.linalg import eig

# ---------------------------------------------------------------- netlist
# (designator, kind, node_a, node_b, value, confidence)  kind: R (ohm) / C (farad)
# nodes: '0' = AC ground. 'inK'/'oK'/'cK' = IC14 stage K input / buffer out / cap node.
PASSIVES = [
    # 68k chain (read directly off the scan)
    ("R114", "R", "in1", "o1", 68e3, "read"),
    ("R117", "R", "o1",  "in2", 68e3, "read"),
    ("R118", "R", "in2", "o2", 68e3, "read"),
    ("R119", "R", "o2",  "in3", 68e3, "read"),
    ("R121", "R", "in3", "o3", 68e3, "read"),
    ("R124", "R", "o3",  "in4", 68e3, "read"),
    ("R122", "R", "in4", "o4", 68e3, "read"),
    # 560 ohm input shunts (return bus: see FINDINGS, bus tie is inferred)
    ("R115", "R", "in1", "0", 560.0, "read"),
    ("R116", "R", "in2", "0", 560.0, "read"),
    ("R120", "R", "in3", "0", 560.0, "read"),
    ("R123", "R", "in4", "0", 560.0, "read"),
    # integrator caps (return to pin-1 reference)
    ("C48", "C", "c1", "0", 240e-12, "read"),   # pin 3
    ("C47", "C", "c2", "0", 240e-12, "read"),   # pin 6
    ("C50", "C", "c3", "0", 240e-12, "read"),   # pin 11
    ("C51", "C", "c4", "0", 240e-12, "read"),   # pin 14
    # input coupling and resonance feedback entry
    ("C45", "C", "sumn", "in1", 10e-6, "read"),
    ("R113", "R", "in1", "clamp", 15e3, "read"),
    ("R129", "R", "clamp", "x52", 5.6e3, "read"),
    ("C52", "C", "x52", "e27", 10e-6, "read"),
    # resonance transistor stage
    ("R131", "R", "e26", "0", 10e3, "read"),
    ("R136", "R", "c26", "sup", 15e3, "read"),
    ("R135", "R", "sup", "0", 1e3, "read"),     # to +V rail (AC ground)
    ("C54", "C", "sup", "0", 10e-6, "read"),
    ("R137", "R", "e27", "0", 33e3, "read (value from errata list)"),
    # output mix to VCA input
    ("R130", "R", "o4", "vca", 150e3, "read"),
    ("R132", "R", "e26", "vca", 150e3, "read"),
    # ASSUMPTION: IC15 (BA662) input network not yet traced; modeled as 1k to AC ground.
    # Leaving this node open creates a spurious loop through R130/R132 and the resonance transistors.
    ("R_VCA_LOAD", "R", "vca", "0", 1e3, "ASSUMED"),
]
MIXER = {"noise": 150e3, "pulse": 680e3, "ramp": 470e3, "sub": 820e3}  # R109..R112 values read; names from Electric Druid
MIXER_DESIG = {"noise": "R109", "pulse": "R110", "ramp": "R111", "sub": "R112"}

NODES = ["in1","o1","in2","o2","in3","o3","in4","o4","c1","c2","c3","c4",
         "sumn","clamp","x52","e27","e26","c26","sup","vca","wip","src"]
IDX = {n: i for i, n in enumerate(NODES)}

# ---------------------------------------------------------------- bias estimate
def bias_estimate(vref=5.0, vsup=15.0, beta=250.0, vbe=0.65, vt=0.02585):
    """DC estimate for TR26/TR27 (2SC1815GR assumed beta). Assumes VR18 wiper sits at the reference."""
    ie26 = (vref - vbe) / 10e3
    vc = 8.0
    for _ in range(100):
        ie27 = (vc - vbe) / 33e3
        vs = vsup - 1e3 * (ie26 + ie27)
        vc = vs - 15e3 * (ie26 + ie27 / (beta + 1))
    return dict(ic26=ie26, ic27=ie27, vc26=vc, vsup_node=vs,
                gm26=ie26 / vt, gm27=ie27 / vt, rpi26=beta * vt / ie26, rpi27=beta * vt / ie27)

# ---------------------------------------------------------------- MNA
def build(gm, alpha, source, rsrc_override=None):
    """Return (G, C) real matrices so that (G + sC) x = b. x = node voltages + 5 aux currents."""
    n = len(NODES)
    N = n + 5  # 4 buffer currents + 1 source current
    G = np.zeros((N, N)); C = np.zeros((N, N)); b = np.zeros(N)

    def stamp(M, a, bb, y):
        ia = None if a == "0" else IDX[a]; ib = None if bb == "0" else IDX[bb]
        if ia is not None: M[ia, ia] += y
        if ib is not None: M[ib, ib] += y
        if ia is not None and ib is not None:
            M[ia, ib] -= y; M[ib, ia] -= y

    for _, kind, a, bb, v, _c in PASSIVES:
        stamp(G if kind == "R" else C, a, bb, 1.0 / v if kind == "R" else v)

    rsrc = rsrc_override if rsrc_override else MIXER[source]
    stamp(G, "src", "sumn", 1.0 / rsrc)

    # VR18 (100k): top = o4, bottom = ref (AC gnd), wiper position alpha from bottom
    a = min(max(alpha, 1e-4), 1 - 1e-4)
    stamp(G, "o4", "wip", 1.0 / ((1 - a) * 100e3))
    stamp(G, "wip", "0", 1.0 / (a * 100e3))

    bias = bias_estimate()
    # TR26: base wip, collector c26, emitter e26
    stamp(G, "wip", "e26", 1.0 / bias["rpi26"])
    g = bias["gm26"]
    G[IDX["c26"], IDX["wip"]] += g; G[IDX["c26"], IDX["e26"]] -= g
    G[IDX["e26"], IDX["wip"]] -= g; G[IDX["e26"], IDX["e26"]] += g
    # TR27: base c26, collector sup, emitter e27
    stamp(G, "c26", "e27", 1.0 / bias["rpi27"])
    g = bias["gm27"]
    G[IDX["sup"], IDX["c26"]] += g; G[IDX["sup"], IDX["e27"]] -= g
    G[IDX["e27"], IDX["c26"]] -= g; G[IDX["e27"], IDX["e27"]] += g

    # OTAs: current leaving cK = gm * V(inK)
    for k in range(1, 5):
        G[IDX[f"c{k}"], IDX[f"in{k}"]] += gm
    # ideal buffers: V(oK) = V(cK); aux current leaves oK
    for k in range(1, 5):
        r = n + k - 1
        G[IDX[f"o{k}"], r] += 1.0
        G[r, IDX[f"o{k}"]] += 1.0; G[r, IDX[f"c{k}"]] -= 1.0
    # source
    r = n + 4
    G[IDX["src"], r] += 1.0; G[r, IDX["src"]] += 1.0; b[r] = 1.0
    return G, C, b

def response(freqs, gm, alpha, source="ramp"):
    G, C, b = build(gm, alpha, source)
    out_f, out_o = [], []
    for f in freqs:
        s = 2j * np.pi * f
        x = np.linalg.solve(G + s * C, b)
        out_f.append(x[IDX["o4"]]); out_o.append(x[IDX["vca"]])
    return np.array(out_f), np.array(out_o)

def poles(gm, alpha):
    G, C, _ = build(gm, alpha, "ramp")
    w = eig(-G, C, right=False)
    w = w[np.isfinite(w)]
    return w

# ---------------------------------------------------------------- calibration from datasheet
R_SIGNAL, R_SHUNT, C_STAGE = 68e3, 560.0, 240e-12
BETA_NODE = 1.0 / (2.0 + R_SIGNAL / R_SHUNT)     # In-node divider: two 68k feeds + 560 shunt
FC0 = 250.0                                     # Hz, datasheet single-stage -3 dB at VC = 0
GM0 = 2 * np.pi * FC0 * C_STAGE / BETA_NODE     # siemens at VC = 0
SENS = 19e-3                                    # V/octave (datasheet typ.)

def gm_at(vc):                                  # vc in volts at pin 9, relative to pin 1
    return GM0 * 2.0 ** (-vc / SENS)

# ---------------------------------------------------------------- CV divider / tempco
def cv_divider(r_th_25=1000.0, B=3500.0, temp_c=25.0):
    """Pin-9 divider: CV bus -> R128 -> [(R126 + TH1) || R127] -> pin 9, R125 to reference.
    TH1 (SDT-1000) type/curve NOT known: modeled as NTC with R25 and B as parameters."""
    T = temp_c + 273.15; T0 = 298.15
    th = r_th_25 * np.exp(B * (1 / T - 1 / T0))
    rp = 1.0 / (1.0 / 5.6e3 + 1.0 / (1.8e3 + th))
    return 820.0 / (820.0 + 4.7e3 + rp)

if __name__ == "__main__":
    print("== Calibration from datasheet ==")
    print(f"node divider = 1/{1/BETA_NODE:.1f}; gm0 at VC=0: {GM0*1e6:.1f} uS")
    b = bias_estimate()
    print(f"TR26 Ic {b['ic26']*1e3:.3f} mA, TR27 Ic {b['ic27']*1e3:.3f} mA, TR26 collector {b['vc26']:.2f} V (estimate)")

    f = np.logspace(0, 5, 600)
    print("\n== Passband gain by source (alpha = 0, VC = 0), VCF out / source at 20 Hz ==")
    for name in MIXER:
        hf, ho = response(np.array([20.0]), GM0, 0.0, name)
        print(f"  {name:6s} ({MIXER_DESIG[name]} {MIXER[name]/1e3:.0f}k): {abs(hf[0]):.3f}  (68k/Rsrc = {68e3/MIXER[name]:.3f})")

    print("\n== 4-pole response, VC = 0, alpha = 0 ==")
    hf, ho = response(f, GM0, 0.0, "ramp")
    mag = 20 * np.log10(np.abs(hf)); dc = mag[np.argmin(abs(f - 20))]
    f3 = f[np.argmax(mag < dc - 3)]
    print(f"  -3 dB at {f3:.1f} Hz (single-stage pole {FC0:.0f} Hz)")
    i1, i2 = np.argmin(abs(f - 10e3)), np.argmin(abs(f - 20e3))
    print(f"  slope 10k->20k: {mag[i2]-mag[i1]:.1f} dB/oct")

    print("\n== Resonance (VR18 wiper alpha) at VC = 0 ==")
    lo, hi = 0.0, 1.0
    for a in [0.2, 0.4, 0.6, 0.7, 0.8]:
        p = poles(GM0, a); p = p[np.abs(p.imag) > 2*np.pi*50]; worst = p[np.argmax(p.real)]
        hf, _ = response(f, GM0, a, "ramp")
        pk = 20 * np.log10(np.abs(hf)).max() - 20 * np.log10(abs(hf[np.argmin(abs(f - 20))]))
        print(f"  alpha {a:.1f}: peak {pk:5.1f} dB above passband, worst pole Re={worst.real:9.1f} rad/s, f={abs(worst.imag)/2/np.pi:6.1f} Hz")
    for _ in range(50):
        mid = (lo + hi) / 2
        if poles(GM0, mid).real.max() > 0: hi = mid
        else: lo = mid
    pc = poles(GM0, hi); pc = pc[np.abs(pc.imag) > 2*np.pi*50]; pw = pc[np.argmax(pc.real)]
    print(f"  self-oscillation threshold alpha = {hi:.3f} (osc at {abs(pw.imag)/2/np.pi:.1f} Hz for gm0 -> ratio to single-stage pole {abs(pw.imag)/2/np.pi/FC0:.2f})")

    print("\n== Output mix weight (R130 from pin 15, R132 from TR26 emitter) vs resonance ==")
    print("  weight = (V_o4 + V_e26) / (2 V_o4), i.e. relative current into the VCA input")
    for a in [0.0, 0.3, 0.6, 0.8]:
        G_, C_, b_ = build(GM0, a, "ramp")
        x = np.linalg.solve(G_ + 2j * np.pi * 20.0 * C_, b_)
        w = (x[IDX["o4"]] + x[IDX["e26"]]) / (2 * x[IDX["o4"]])
        print(f"  alpha {a:.1f}: {abs(w):.3f}")

    print("\n== Cutoff CV divider at pin 9 ==")
    g = cv_divider()
    print(f"  divider ratio (TH1 assumed 1k NTC, B=3500): {g:.4f}  -> CV bus needs {SENS*1e3/g:.0f} mV per octave")
    print("  divider tempco vs chip tempco (+0.33 %/degC needed):")
    for B in (3000., 3500., 4000.):
        g1, g2 = cv_divider(B=B, temp_c=24.0), cv_divider(B=B, temp_c=26.0)
        print(f"    TH1 B={B:.0f} K: {100*(np.log(g2/g1))/2:+.3f} %/degC")
