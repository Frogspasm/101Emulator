#!/usr/bin/env node
/*
 * Builds 101dev/index.html from tools/index.template.html and docs/sh101_core.js.
 *
 * The core is placed twice, as the handoff requires:
 *   1. a plain <script> before the app script (runs the core on the page), and
 *   2. a <script type="text/plain" id="core-src"> block, which the AudioWorklet loader reads as text.
 * Both come from the same file, so they cannot drift apart.
 *
 * Usage: node tools/build_index.js
 */
"use strict";
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");
const corePath = path.join(root, "docs", "sh101_core.js");
const templatePath = path.join(__dirname, "index.template.html");
const outPath = path.join(root, "index.html");

const core = fs.readFileSync(corePath, "utf8").replace(/\s*$/, "\n");
const template = fs.readFileSync(templatePath, "utf8");

// The text block must not contain a literal closing script tag.
const srcText = core.replace(/<\/script/gi, "<\\/script");
const coreScript = "<script>\n" + core + "</script>";
const coreSrc = '<script type="text/plain" id="core-src">\n' + srcText + "</script>";

// Use replacer functions so "$" sequences in the core are never interpreted.
let html = template
  .replace("<!--CORE_SCRIPT-->", () => coreScript)
  .replace("<!--CORE_SRC-->", () => coreSrc);

if (html.includes("<!--CORE_")) throw new Error("a core placeholder was not replaced");

fs.writeFileSync(outPath, html);
console.log(`wrote ${path.relative(process.cwd(), outPath) || outPath} (${html.length} bytes, core ${core.length} bytes x2)`);
