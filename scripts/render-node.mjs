/**
 * render-node.mjs — Deterministic single-frame Lottie rendering in Node,
 * using the official dotlottie runtime + @napi-rs/canvas. Reads SRC (file),
 * FRAME_PCT (0-100) and writes a PNG to OUT. Bit-exact across machines,
 * which makes it the source of truth for visual regression tests.
 *
 * Env: SRC=<animation.lottie|.json> FRAME_PCT=50 OUT=frame-50.png
 */
import fs from "node:fs";
import path from "node:path";
import { DotLottie } from "@lottiefiles/dotlottie-web";
import { createCanvas } from "@napi-rs/canvas";

const src = process.env.SRC;
const pct = Number(process.env.FRAME_PCT || 0);
const out = process.env.OUT || "frame.png";
const SIZE = Number(process.env.RENDER_SIZE || 512);

if (!src) {
  console.error("usage: SRC=<file> FRAME_PCT=<0-100> OUT=<png> node render-node.mjs");
  process.exit(1);
}

const canvas = createCanvas(SIZE, SIZE);
const sourcePath = path.resolve(src);
if (!fs.existsSync(sourcePath)) {
  console.error(`source file not found: ${sourcePath}`);
  process.exit(1);
}
const bytes = fs.readFileSync(sourcePath);
const data = sourcePath.endsWith(".json")
  ? JSON.parse(bytes.toString("utf8"))
  : new Uint8Array(bytes);

const dotLottie = new DotLottie({
  canvas,
  data,
  autoplay: false,
  renderConfig: { devicePixelRatio: 1 },
});

dotLottie.addEventListener("load", async () => {
  const target = Math.round((pct / 100) * (dotLottie.totalFrames - 1));
  dotLottie.setFrame(target);
  fs.writeFileSync(out, await canvas.encode("png"));
  dotLottie.destroy();
  process.exit(0);
});

dotLottie.addEventListener("loadError", (e) => {
  console.error("loadError:", e);
  process.exit(2);
});
