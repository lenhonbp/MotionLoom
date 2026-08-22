#!/usr/bin/env node
/**
 * Deterministic target-canvas adaptation for provider outputs.
 * This command never calls a provider and never crops or stretches silently.
 */
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { createCanvas, loadImage } from "@napi-rs/canvas";

function usage() {
  console.error("usage: motionloom asset-adapt pad --input source.png --output target.png --width W --height H [--scale N] [--anchor center|footline] [--report report.json] [--json]");
}

function arg(name, fallback = undefined) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : fallback;
}

function required(name) {
  const value = arg(name);
  if (!value) throw new Error(`${name} is required`);
  return value;
}

function sha256(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

function inside(root, file) {
  const relative = path.relative(root, file);
  return relative && !relative.startsWith("..") && !path.isAbsolute(relative);
}

async function main() {
  const operation = process.argv[2];
  if (operation !== "pad") {
    usage();
    process.exitCode = 2;
    return;
  }
  const input = path.resolve(required("--input"));
  const output = path.resolve(required("--output"));
  const width = Number(required("--width"));
  const height = Number(required("--height"));
  const scale = Number(arg("--scale", "1"));
  const anchor = arg("--anchor", "footline");
  const reportPath = arg("--report");
  if (!fs.existsSync(input)) throw new Error(`input not found: ${input}`);
  if (!Number.isInteger(width) || width < 1 || !Number.isInteger(height) || height < 1) throw new Error("target width/height must be positive integers");
  if (!Number.isInteger(scale) || scale < 1) throw new Error("scale must be a positive integer");
  if (!["center", "footline"].includes(anchor)) throw new Error("anchor must be center or footline");
  if (input === output) throw new Error("input and output must be different files");
  const image = await loadImage(input);
  const scaledWidth = image.width * scale;
  const scaledHeight = image.height * scale;
  if (scaledWidth > width || scaledHeight > height) {
    throw new Error(`source ${image.width}x${image.height} at integer scale ${scale} exceeds target ${width}x${height}; crop is forbidden`);
  }
  const x = Math.floor((width - scaledWidth) / 2);
  const y = anchor === "footline" ? height - scaledHeight : Math.floor((height - scaledHeight) / 2);
  const canvas = createCanvas(width, height);
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, width, height);
  context.imageSmoothingEnabled = false;
  context.drawImage(image, x, y, scaledWidth, scaledHeight);
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, await canvas.encode("png"));
  const report = {
    contract: "motionloom-asset-adaptation",
    schema_version: "0.1",
    operation: "pad",
    status: "built",
    approval: false,
    production_approved: false,
    source: { path: input, sha256: sha256(input), canvas: [image.width, image.height] },
    output: { path: output, sha256: sha256(output), canvas: [width, height] },
    transform: { scale, x, y, anchor, crop: false, stretch: false, interpolation: "nearest-neighbour" },
    note: "Deterministic transparent canvas adaptation; visual and frame/action contracts remain required.",
  };
  if (reportPath) {
    const reportAbsolute = path.resolve(reportPath);
    fs.mkdirSync(path.dirname(reportAbsolute), { recursive: true });
    fs.writeFileSync(reportAbsolute, JSON.stringify(report, null, 2) + "\n");
  }
  console.log(JSON.stringify(report, null, 2));
}

main().catch((error) => {
  console.error(`asset-adapt blocked: ${error.message}`);
  process.exitCode = 2;
});
