#!/usr/bin/env node
/**
 * Cross-platform npm prepack cleanup. Do not rely on find/rm so publishing
 * from PowerShell, macOS and Linux produces the same tarball.
 */
import { readdir, lstat, rm } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(fileURLToPath(new URL("..", import.meta.url)));
const ignoredDirectories = new Set(["node_modules", ".git", ".venv", "venv"]);

async function clean(directory) {
  let entries = [];
  try {
    entries = await readdir(directory, { withFileTypes: true });
  } catch {
    return;
  }
  await Promise.all(entries.map(async (entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      if (ignoredDirectories.has(entry.name)) return;
      if (entry.name === "__pycache__") {
        await rm(path, { recursive: true, force: true });
        return;
      }
      await clean(path);
      return;
    }
    if (entry.isFile() && /\.(pyc|pyo)$/.test(entry.name)) {
      await rm(path, { force: true });
    }
  }));
}

await clean(root);
