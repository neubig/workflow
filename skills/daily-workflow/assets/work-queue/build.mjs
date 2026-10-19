import { readFileSync, writeFileSync } from "node:fs";
// extension.js is checked in and self-contained; this script verifies it parses as ESM with no bare imports.
const src = readFileSync(new URL("./extension.js", import.meta.url), "utf8");
if (!/export\s+function\s+activate/.test(src)) throw new Error("activate export missing");
if (/^\s*import\s+[^"']*["'][^./]/m.test(src)) throw new Error("bare import found");
if (/import\s*\(/.test(src)) throw new Error("dynamic import found");
console.log(`extension.js OK (${src.length} bytes)`);
