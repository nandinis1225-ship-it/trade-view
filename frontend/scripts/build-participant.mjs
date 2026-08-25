#!/usr/bin/env node
/**
 * Participant static export — excludes admin/developer/market-screen at compile time.
 * Restores source routes after build so the developer tree is unchanged.
 */
import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");
const appDir = path.join(root, "src", "app");
const stashDir = path.join(root, ".participant-stash");
const excludeRoutes = ["admin", "developer", "market-screen", "projector"];

function stashRoutes() {
  fs.mkdirSync(stashDir, { recursive: true });
  for (const name of excludeRoutes) {
    const src = path.join(appDir, name);
    const dest = path.join(stashDir, name);
    if (fs.existsSync(src)) {
      if (fs.existsSync(dest)) fs.rmSync(dest, { recursive: true, force: true });
      fs.renameSync(src, dest);
    }
  }
}

function restoreRoutes() {
  for (const name of excludeRoutes) {
    const src = path.join(stashDir, name);
    const dest = path.join(appDir, name);
    if (fs.existsSync(src)) {
      if (fs.existsSync(dest)) fs.rmSync(dest, { recursive: true, force: true });
      fs.renameSync(src, dest);
    }
  }
  if (fs.existsSync(stashDir)) fs.rmSync(stashDir, { recursive: true, force: true });
}

function pruneOutRoutes() {
  for (const name of excludeRoutes) {
    const outDir = path.join(root, "out", name);
    if (fs.existsSync(outDir)) fs.rmSync(outDir, { recursive: true, force: true });
  }
}

stashRoutes();
try {
  execSync("npm run build", {
    cwd: root,
    env: { ...process.env, PARTICIPANT_BUILD: "1" },
    stdio: "inherit",
  });
  pruneOutRoutes();
} finally {
  restoreRoutes();
}

console.log("Participant frontend build complete (developer routes excluded at compile time).");
