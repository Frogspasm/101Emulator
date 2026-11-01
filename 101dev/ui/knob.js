// AcidBox knob: a rotary dial that reads and writes one setting.
//
// Needs these from the surrounding app:
//   state.params           object holding each setting's current value (0 to 1), keyed by id
//   setParam(id, value)    stores the new value and sends it to the sound engine
//
// Usage:
//   document.body.appendChild(buildKnob({ id: 'cutoff', label: 'Cutoff', def: 0.35 }));
//   buildKnob({ id, label, def, fmt })
//     id     the setting this knob controls
//     label  text shown under the dial
//     def    default value (0 to 1), used for double-click or double-tap reset
//     fmt    optional: turns a 0..1 value into display text, e.g. v => Math.round(v * 100) + '%'

const A0 = Math.PI * 0.75, SPAN = Math.PI * 1.5;   // dial runs from 7:30 to 4:30, 270 degrees

function arc(r, a0, a1) {
  const x0 = 32 + r * Math.cos(a0), y0 = 32 + r * Math.sin(a0);
  const x1 = 32 + r * Math.cos(a1), y1 = 32 + r * Math.sin(a1);
  return `M${x0.toFixed(2)} ${y0.toFixed(2)} A${r} ${r} 0 ${a1 - a0 > Math.PI ? 1 : 0} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`;
}

const clamp = v => Math.min(1, Math.max(0, v));
const knobDraw = {};   // redraws every knob bound to a setting, by setting id

function buildKnob(k) {
  const el = document.createElement('div');
  el.className = 'knob';
  el.dataset.pid = k.id;
  el.tabIndex = 0;
  el.setAttribute('role', 'slider');
  el.setAttribute('aria-label', k.label);
  el.setAttribute('aria-valuemin', '0');
  el.setAttribute('aria-valuemax', '100');
  el.innerHTML = `<svg viewBox="0 0 64 64" aria-hidden="true">
      <path d="${arc(28, A0, A0 + SPAN)}" fill="none" stroke="var(--track)" stroke-width="4" stroke-linecap="round"/>
      <path class="val" fill="none" stroke="var(--led)" stroke-width="4" stroke-linecap="round"/>
      <circle cx="32" cy="32" r="21" fill="var(--knob-body)"/>
      <line class="ind" x1="32" y1="32" stroke="var(--knob-mark)" stroke-width="3.5" stroke-linecap="round"/>
    </svg><span class="klabel">${k.label}</span><span class="kval"></span>`;

  const valPath = el.querySelector('.val'), ind = el.querySelector('.ind'), out = el.querySelector('.kval');
  const fmt = k.fmt || (v => Math.round(v * 100));

  function draw() {
    const v = state.params[k.id], a = A0 + v * SPAN;
    valPath.setAttribute('d', v > 0.004 ? arc(28, A0, a) : '');   // the filled part of the ring
    ind.setAttribute('x2', (32 + 16 * Math.cos(a)).toFixed(2));  // the pointer
    ind.setAttribute('y2', (32 + 16 * Math.sin(a)).toFixed(2));
    out.textContent = fmt(v);
    el.setAttribute('aria-valuenow', Math.round(v * 100));
    el.setAttribute('aria-valuetext', String(fmt(v)));
  }

  function set(v) { setParam(k.id, clamp(v)); knobDraw[k.id](); }

  // drag up or down to change; hold Shift for fine control
  let startY = 0, startV = 0, dragging = false, pendingV = null;
  el.addEventListener('pointerdown', e => {
    dragging = true; startY = e.clientY; startV = state.params[k.id];
    el.setPointerCapture(e.pointerId); e.preventDefault();
  });
  el.addEventListener('pointermove', e => {
    if (!dragging) return;
    const v = startV + (startY - e.clientY) / (e.shiftKey ? 700 : 180);
    // phones can fire 120+ moves a second; apply at most one per screen frame
    if (pendingV === null) requestAnimationFrame(() => { const x = pendingV; pendingV = null; set(x); });
    pendingV = v;
  });
  const end = () => { dragging = false; };
  el.addEventListener('pointerup', end);
  el.addEventListener('pointercancel', end);

  // double-click or double-tap resets to the default
  el.addEventListener('dblclick', () => set(k.def));
  let lastTap = 0;
  el.addEventListener('pointerup', e => {
    if (e.pointerType !== 'touch') return;
    const now = Date.now();
    if (now - lastTap < 300 && Math.abs(e.clientY - startY) < 6) set(k.def);
    lastTap = now;
  });

  // keyboard: arrows nudge, PageUp/PageDown jump, Home and End go to the ends
  el.addEventListener('keydown', e => {
    const v = state.params[k.id];
    const steps = { ArrowUp: 0.01, ArrowRight: 0.01, ArrowDown: -0.01, ArrowLeft: -0.01, PageUp: 0.1, PageDown: -0.1 };
    if (e.key in steps) { set(v + steps[e.key]); e.preventDefault(); }
    else if (e.key === 'Home') { set(0); e.preventDefault(); }
    else if (e.key === 'End') { set(1); e.preventDefault(); }
  });

  draw();
  // several knobs can share one setting, so keep them all in step
  const prev = knobDraw[k.id];
  knobDraw[k.id] = prev ? () => { prev(); draw(); } : draw;
  return el;
}
