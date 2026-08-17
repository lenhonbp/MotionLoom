#!/usr/bin/env node
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const labRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = path.resolve(labRoot, "..");
const fixtureRoot = fs.mkdtempSync(path.join(os.tmpdir(), "motionloom-devlab-security-"));
const publicRoot = path.join(fixtureRoot, "public");
const scene = "browser-review-smoke";
const sceneRoot = path.join(publicRoot, "scenes", scene);
fs.mkdirSync(path.dirname(sceneRoot), { recursive: true });
fs.copyFileSync(path.join(labRoot, "public", "index.html"), path.join(publicRoot, "index.html"));
fs.copyFileSync(path.join(labRoot, "public", "devlab.js"), path.join(publicRoot, "devlab.js"));
fs.cpSync(path.join(repositoryRoot, "src", "output", scene), sceneRoot, { recursive: true });

const manifestPath = path.join(sceneRoot, "manifest.json");
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
const attack = `<img src=x onerror="document.body.dataset.motionloomXss='executed'">`;
manifest.checks = [{ id: "xss-check", label: attack, detail: attack }];
fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);

const candidatePath = path.join(sceneRoot, "browser-review.json");
const candidate = JSON.parse(fs.readFileSync(candidatePath, "utf8"));
candidate.status = "prepared";
candidate.expires_at = "2099-01-01T00:00:00Z";
fs.writeFileSync(candidatePath, `${JSON.stringify(candidate, null, 2)}\n`);

const contentTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".png", "image/png"],
]);
const server = http.createServer((request, response) => {
  const pathname = decodeURIComponent(new URL(request.url, "http://127.0.0.1").pathname);
  const relative = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  const target = path.resolve(publicRoot, relative);
  if (target !== publicRoot && !target.startsWith(`${publicRoot}${path.sep}`)) {
    response.writeHead(403).end("forbidden");
    return;
  }
  try {
    response.writeHead(200, {
      "Content-Type": contentTypes.get(path.extname(target)) || "application/octet-stream",
      "Cache-Control": "no-store",
    });
    response.end(fs.readFileSync(target));
  } catch {
    response.writeHead(404).end("not found");
  }
});

let browser;
try {
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  const baseUrl = `http://127.0.0.1:${address.port}/?scene=${scene}&task_id=${encodeURIComponent(candidate.task_id)}&candidate_id=${encodeURIComponent(candidate.candidate_id)}`;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__lab?.ready === true);
  const safeDom = await page.evaluate((expected) => ({
    injectedElement: Boolean(document.querySelector("#checks img")),
    executed: document.body.dataset.motionloomXss || null,
    visibleAsText: document.querySelector("#checks")?.textContent?.includes(expected) || false,
  }), attack);
  if (safeDom.injectedElement || safeDom.executed || !safeDom.visibleAsText) {
    throw new Error(`Dev Lab DOM injection regression: ${JSON.stringify(safeDom)}`);
  }

  candidate.status = "approved";
  fs.writeFileSync(candidatePath, `${JSON.stringify(candidate, null, 2)}\n`);
  const terminalPage = await browser.newPage();
  await terminalPage.goto(`${baseUrl}&terminal_probe=1`, { waitUntil: "networkidle" });
  await terminalPage.waitForFunction(() => document.querySelector("#status")?.textContent?.includes("not reviewable"));
  const terminalReady = await terminalPage.evaluate(() => window.__lab?.ready);
  await terminalPage.close();
  if (terminalReady !== false) throw new Error("Terminal candidate became reviewable");

  candidate.status = "prepared";
  candidate.expires_at = "2000-01-01T00:00:00Z";
  fs.writeFileSync(candidatePath, `${JSON.stringify(candidate, null, 2)}\n`);
  const expiredPage = await browser.newPage();
  await expiredPage.goto(`${baseUrl}&expired_probe=1`, { waitUntil: "networkidle" });
  await expiredPage.waitForFunction(() => document.querySelector("#status")?.textContent?.includes("expired"));
  const expiredReady = await expiredPage.evaluate(() => window.__lab?.ready);
  await expiredPage.close();
  if (expiredReady !== false) throw new Error("Expired candidate became reviewable");

  console.log(JSON.stringify({
    status: "pass",
    dom_injection: "blocked",
    terminal_candidate: "blocked",
    expired_candidate: "blocked",
  }, null, 2));
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
  fs.rmSync(fixtureRoot, { recursive: true, force: true });
}
