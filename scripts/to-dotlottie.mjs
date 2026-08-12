#!/usr/bin/env node
/**
 * Deterministic dotLottie v2 packager.
 * The scene manifest stays outside the archive; the archive contains the
 * standard manifest.json plus the Lottie payload under a/.
 */
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";

function arg(name, fallback = undefined) {
  const index = process.argv.indexOf(name);
  return index === -1 ? fallback : process.argv[index + 1];
}

const sceneDir = path.resolve(arg("--scene-dir", ""));
const output = path.resolve(arg("--output", ""));
const generator = arg("--generator", "animation-skill-kit/to-dotlottie");
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

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "animation-skill-dotlottie-"));
const archiveRoot = path.join(tmp, "archive");
fs.mkdirSync(path.join(archiveRoot, "a"), { recursive: true });
fs.copyFileSync(sourcePath, path.join(archiveRoot, "a", `${animationId}.json`));

const optionalDirectories = ["i", "t", "s", "f"];
for (const directory of optionalDirectories) {
  const candidate = path.join(sceneDir, "dotlottie", directory);
  if (fs.existsSync(candidate)) {
    fs.cpSync(candidate, path.join(archiveRoot, directory), { recursive: true });
  }
}

const dotManifest = {
  version: "2",
  generator,
  initial: { animation: animationId },
  animations: [{ id: animationId }],
};
fs.writeFileSync(
  path.join(archiveRoot, "manifest.json"),
  `${JSON.stringify(dotManifest, null, 2)}\n`,
  "utf8",
);

fs.mkdirSync(path.dirname(output), { recursive: true });
if (fs.existsSync(output)) fs.rmSync(output, { force: true });
execFileSync("zip", ["-X", "-q", "-r", output, "."], { cwd: archiveRoot });

const entries = execFileSync("unzip", ["-Z1", output], { encoding: "utf8" })
  .trim()
  .split(/\r?\n/)
  .filter(Boolean);
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
  return JSON.parse(execFileSync("unzip", ["-p", file, entry], { encoding: "utf8" }));
}
