"""
Pulse-width model for the SH-101 VCO (guess G17: PW pot is linear, duty = 0.5 * wiper,
spec range 50% .. 0%). PWM from the envelope (G18: full envelope swing moves duty by 0.25).
Uses PolyBLEP on both edges so the pulse stays clean.
"""
import numpy as np
from scipy.io import wavfile
from sh101_guessed import FS, vco_hz, envelope, ladder

def polyblep(t, dt):
    t = t % 1.0; out = np.zeros_like(t)
    m = t < dt; x = t[m]/dt; out[m] = 2*x - x*x - 1.0
    m2 = t > 1-dt; x = (t[m2]-1)/dt; out[m2] = x*x + 2*x + 1.0
    return out

def pulse(freq, duty_arr):
    n = len(duty_arr)
    dt = freq/FS
    ph = np.cumsum(np.full(n, dt)) % 1.0
    d = np.clip(duty_arr, 0.01, 0.99)
    y = np.where(ph < d, 1.0, -1.0)
    # PolyBLEP at rising edge (phase 0) and falling edge (phase d)
    y += -polyblep(ph, dt)
    y += polyblep((ph - d) % 1.0, dt)
    return y

def duty_from_pot(wiper):
    """G17: duty runs linearly from 0.5 (wiper=1) down to 0 (wiper=0); clamp to 1%."""
    return np.clip(0.5*wiper, 0.01, 0.5)

def mark_space_ratio(duty):
    return duty/(1-duty)

if __name__ == "__main__":
    # 1. PW setting vs duty, plus the service-manual 1:1 point
    print("PW wiper   duty   mark:space")
    for w in [1.0, 0.8, 0.6, 0.4, 0.2]:
        d = duty_from_pot(w)
        print(f"  {w:4.1f}   {d*100:5.1f}%   {mark_space_ratio(d):5.2f}")
    print("Service manual 1:1 mark/space is a 50% duty point: reached at wiper = 1.0 (G17).")
    print("Note: the manual's 1:1 adjustment is VR-2 (D/A TUNE) with the waveform set to pulse,")
    print("so it checks the D/A path rather than the PW pot.")

    # 2. PWM depth: envelope moves duty by up to 0.25 (G18)
    seq = [(33,0.5),(40,0.5),(45,0.5),(48,0.5),(45,0.5),(40,0.5),(33,0.75)]
    pieces=[]
    for i,(note,dur) in enumerate(seq):
        n = int((dur+0.25)*FS); f = vco_hz(note)
        env = envelope(n, 0.005, 0.25, 0.35, 0.25, dur)
        wiper = 0.7
        duty = np.clip(duty_from_pot(wiper) + 0.25*env*0.5, 0.01, 0.49)  # G18
        osc = pulse(f, duty)
        cut = 1000.0 * 2**(3.5*env)
        pieces.append(ladder(osc*0.6, cut, min(1.0+0.4*i, 3.6))*env)
    audio = np.concatenate(pieces); audio = audio/(np.max(np.abs(audio))+1e-9)*0.8
    wavfile.write("sh101_pulse_pwm.wav", FS, (audio*32767).astype(np.int16))
    print(f"wrote sh101_pulse_pwm.wav ({len(audio)/FS:.1f} s)")
