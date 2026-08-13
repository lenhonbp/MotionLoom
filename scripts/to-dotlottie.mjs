#!/usr/bin/env node
/**
 * Deterministic dotLottie v2 packager.
 * The scene manifest stays outside the archive; the archive contains the
 * standard manifest.json plus the Lottie payload under a/.
 */
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { strFromU8, zipSync, unzipSync } from "fflate";

function arg(name, fallback = undefined) {
  const index = process.argv.indexOf(name);
  return index === -1 ? fallback : process.argv[index + 1];
}

const sceneDir = path.resolve(arg("--scene-dir", ""));
const output = path.resolve(arg("--output", ""));
const generator = arg("--generator", "motionloom/to-dotlottie");
if (!sceneDir || !output) throw new Error("--scene-dir and --output are required");

const readJson = (file) => JSON.parse(fs.readFileSync(file, "utf8"));
const sceneManifestPath = path.join(sceneDir, "manifest.json");
if (!fs.existsSync(sceneManifestPath)) throw new Error("scene manifest.json is required");
const sceneManifest = readJson(sceneManifestPath);
const source = sceneManifest.file;
if (typeof source !== "string" || !source || path.isAbsolute(source) || source.includes("..")) {
  throw new Error("scene manifest.file must be a relative path without traversal");
}
const sourcePath = path.resolve(sceneDir, source);
if (!sourcePath.startsWith(`${sceneDir}${path.sep}`) || !fs.existsSync(sourcePath)) {
  throw new Error(`scene source does not exist inside scene directory: ${source}`);
}
if (path.extname(sourcePath).toLowerCase() !== ".json") {
  throw new Error("dotLottie packager currently accepts a Lottie JSON scene source");
}

const animationId = String(arg("--animation-id", path.basename(sourcePath, ".json")))
  .trim();
if (!/^[a-zA-Z0-9._ -]+$/.test(animationId)) {
  throw new Error(`invalid dotLottie animation id: ${animationId}`);
}
readJson(sourcePath);

const archive = {
  [`a/${animationId}.json`]: fs.readFileSync(sourcePath),
};

const optionalDirectories = ["i", "t", "s", "f"];
for (const directory of optionalDirectories) {
  const candidate = path.join(sceneDir, "dotlottie", directory);
  if (fs.existsSync(candidate)) addTree(candidate, directory);
}

const dotManifest = {
  version: "2",
  generator,
  initial: { animation: animationId },
  animations: [{ id: animationId }],
};
archive["manifest.json"] = Buffer.from(`${JSON.stringify(dotManifest, null, 2)}\n`, "utf8");

fs.mkdirSync(path.dirname(output), { recursive: true });
if (fs.existsSync(output)) fs.rmSync(output, { force: true });
fs.writeFileSync(output, zipSync(archive, { level: 6 }));

const entries = Object.keys(unzipSync(fs.readFileSync(output))).sort();
if (!entries.includes("manifest.json")) throw new Error("archive missing manifest.json");
if (!entries.includes(`a/${animationId}.json`)) {
  throw new Error("archive missing initial animation payload");
}
const packagedManifest = readJsonFromZip(output, "manifest.json");
if (packagedManifest.version !== "2") throw new Error("dotLottie manifest version must be 2");
if (packagedManifest.initial?.animation !== animationId) {
  throw new Error("dotLottie initial.animation does not match packaged animation");
}
const hash = crypto.createHash("sha256").update(fs.readFileSync(output)).digest("hex");
console.log(JSON.stringify({
  output,
  bytes: fs.statSync(output).size,
  sha256: hash,
  manifest: packagedManifest,
  entries,
}, null, 2));

function readJsonFromZip(file, entry) {
  const payload = unzipSync(fs.readFileSync(file))[entry];
  if (!payload) throw new Error(`archive entry is missing: ${entry}`);
  return JSON.parse(strFromU8(payload));
}

function addTree(directory, archivePrefix) {
  const entries = fs.readdirSync(directory, { withFileTypes: true });
  for (const entry of entries) {
    const sourceEntry = path.join(directory, entry.name);
    const archiveEntry = `${archivePrefix}/${entry.name.replaceAll("\\", "/")}`;
    const stat = fs.lstatSync(sourceEntry);
    if (stat.isSymbolicLink()) continue;
    if (stat.isDirectory()) {
      addTree(sourceEntry, archiveEntry);
    } else if (stat.isFile()) {
      archive[archiveEntry] = fs.readFileSync(sourceEntry);
    }
  }
}
