#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const labRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = path.join(labRoot, "public");
const destination = path.join(labRoot, "dist");
for (const relative of ["index.html", "devlab.js"]) {
  if (!fs.existsSync(path.join(source, relative))) {
    throw new Error(`Dev Lab build input is missing: public/${relative}`);
  }
}
fs.rmSync(destination, { recursive: true, force: true });
fs.cpSync(source, destination, { recursive: true });
console.log(`Dev Lab static build: ${destination}`);
