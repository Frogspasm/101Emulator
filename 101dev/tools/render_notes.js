#!/usr/bin/env node
/*
 * Render a note list with the SH-101 core (docs/sh101_core.js) to a 16-bit mono WAV.
 *
 * Usage:
 *   node tools/render_notes.js notes.txt out.wav [patch]
 *
 * notes.txt has one note per line: midi_note  start_seconds  duration_seconds
 * Lines starting with # are comments. Patch names come from the core's PATCHES
 * (bass, pwm, whistle). Output is peak-normalised to 0.8, as the old Python renderer was.
 *
 * Noise comes from the core's seeded generator, so renders are identical run to run.
 */
"use strict";
const fs = require("fs");
const path = require("path");

const SH = require(path.join(__dirname, "..", "docs", "sh101_core.js"));

const FS = 44100;
const BLOCK = 512;
const TAIL_S = 2.0;          // extra time after the last note so releases finish

function loadNotes(file) {
  const notes = [];
  for (const raw of fs.readFileSync(file, "utf8").split("\n")) {
    const line = raw.split("#")[0].trim();
    if (!line) continue;
    const parts = line.split(/\s+/);
    if (parts.length !== 3) throw new Error(`bad line (need 3 fields): ${raw}`);
    const [midi, start, dur] = parts.map(Number);
    if (![midi, start, dur].every(Number.isFinite)) throw new Error(`non-numeric field: ${raw}`);
    notes.push({ midi, start, dur });
  }
  if (notes.length === 0) throw new Error(`no notes found in ${file}`);
  return notes;
}

function renderNotes(notes, patch) {
  // Events sorted by time; at equal times, note-offs come before note-ons so repeated notes retrigger.
  const events = [];
  let end = 0;
  for (const n of notes) {
    events.push({ t: n.start, on: true, midi: n.midi });
    events.push({ t: n.start + n.dur, on: false, midi: n.midi });
    end = Math.max(end, n.start + n.dur);
  }
  events.sort((a, b) => a.t - b.t || (a.on === b.on ? 0 : a.on ? 1 : -1));

  const total = Math.ceil((end + TAIL_S) * FS);
  const out = new Float32Array(total);
  const voice = new SH.Voice(FS, patch);

  let ei = 0, pos = 0;
  while (pos < total) {
    // apply every event that falls at or before this sample
    while (ei < events.length && Math.round(events[ei].t * FS) <= pos) {
      const ev = events[ei++];
      if (ev.on) voice.noteOn(ev.midi); else voice.noteOff(ev.midi);
    }
    // render up to the next event or one block, whichever comes first
    const nextEv = ei < events.length ? Math.round(events[ei].t * FS) : total;
    const stop = Math.min(total, Math.max(nextEv, pos + 1), pos + BLOCK);
    const n = stop - pos;
    const buf = new Float32Array(n);
    voice.render(buf, n);
    out.set(buf, pos);
    pos += n;
  }
  return out;
}

function normalise(x, peak = 0.8) {
  let m = 0;
  for (let i = 0; i < x.length; i++) m = Math.max(m, Math.abs(x[i]));
  const g = m > 0 ? peak / m : 0;
  for (let i = 0; i < x.length; i++) x[i] *= g;
  return x;
}

function writeWav(file, x) {
  const dataBytes = x.length * 2;
  const buf = Buffer.alloc(44 + dataBytes);
  buf.write("RIFF", 0);
  buf.writeUInt32LE(36 + dataBytes, 4);
  buf.write("WAVE", 8);
  buf.write("fmt ", 12);
  buf.writeUInt32LE(16, 16);          // PCM chunk size
  buf.writeUInt16LE(1, 20);           // PCM
  buf.writeUInt16LE(1, 22);           // mono
  buf.writeUInt32LE(FS, 24);
  buf.writeUInt32LE(FS * 2, 28);      // byte rate
  buf.writeUInt16LE(2, 32);           // block align
  buf.writeUInt16LE(16, 34);          // bits per sample
  buf.write("data", 36);
  buf.writeUInt32LE(dataBytes, 40);
  for (let i = 0; i < x.length; i++) {
    const v = Math.max(-1, Math.min(1, x[i]));
    buf.writeInt16LE(Math.round(v * 32767), 44 + 2 * i);
  }
  fs.writeFileSync(file, buf);
}

function main(argv) {
  if (argv.length < 2) {
    console.error("usage: node tools/render_notes.js notes.txt out.wav [patch]");
    process.exit(1);
  }
  const [notesFile, outFile, patchName = "bass"] = argv;
  if (!Object.prototype.hasOwnProperty.call(SH.PATCHES, patchName)) {
    console.error(`unknown patch ${JSON.stringify(patchName)}; choose from ${Object.keys(SH.PATCHES).join(", ")}`);
    process.exit(1);
  }
  const notes = loadNotes(notesFile);
  const x = normalise(renderNotes(notes, SH.PATCHES[patchName]));
  writeWav(outFile, x);
  console.log(`wrote ${outFile} (${(x.length / FS).toFixed(1)} s) with patch '${patchName}'`);
}

if (require.main === module) main(process.argv.slice(2));

module.exports = { loadNotes, renderNotes, normalise, writeWav };
