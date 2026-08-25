#!/usr/bin/env node
/**
 * Projector static export — public market display only (no participant/admin/developer routes).
 */
import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");
const appDir = path.join(root, "src", "app");
const stashDir = path.join(root, ".projector-stash");
const keepRoutes = new Set(["projector", "layout.tsx", "globals.css", "page.tsx", "favicon.ico"]);

function stashRoutes() {
  fs.mkdirSync(stashDir, { recursive: true });
  for (const entry of fs.readdirSync(appDir, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    if (keepRoutes.has(entry.name)) continue;
    const src = path.join(appDir, entry.name);
    const dest = path.join(stashDir, entry.name);
    if (fs.existsSync(dest)) fs.rmSync(dest, { recursive: true, force: true });
    fs.renameSync(src, dest);
  }
}

function restoreRoutes() {
  if (!fs.existsSync(stashDir)) return;
  for (const entry of fs.readdirSync(stashDir, { withFileTypes: true })) {
    const src = path.join(stashDir, entry.name);
    const dest = path.join(appDir, entry.name);
    if (fs.existsSync(dest)) fs.rmSync(dest, { recursive: true, force: true });
    fs.renameSync(src, dest);
  }
  fs.rmSync(stashDir, { recursive: true, force: true });
}

function pruneOutRoutes() {
  if (!fs.existsSync(path.join(root, "out"))) return;
  for (const entry of fs.readdirSync(path.join(root, "out"), { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    if (entry.name === "projector" || entry.name === "_next") continue;
    fs.rmSync(path.join(root, "out", entry.name), { recursive: true, force: true });
  }
}

// Redirect home to projector during projector build
const homePath = path.join(appDir, "page.tsx");
const homeBackup = path.join(stashDir, "page.tsx.home");
const projectorHome = `"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/projector");
  }, [router]);
  return null;
}
`;

function cleanNextCache() {
  const nextDir = path.join(root, ".next");
  const outDir = path.join(root, "out");
  if (fs.existsSync(nextDir)) fs.rmSync(nextDir, { recursive: true, force: true });
  if (fs.existsSync(outDir)) fs.rmSync(outDir, { recursive: true, force: true });
}

stashRoutes();
fs.mkdirSync(stashDir, { recursive: true });
if (fs.existsSync(homePath)) fs.copyFileSync(homePath, homeBackup);
fs.writeFileSync(homePath, projectorHome, "utf8");

try {
  cleanNextCache();
  execSync("npm run build", {
    cwd: root,
    env: { ...process.env, PARTICIPANT_BUILD: "1", PROJECTOR_BUILD: "1" },
    stdio: "inherit",
  });
  pruneOutRoutes();
} finally {
  if (fs.existsSync(homeBackup)) {
    fs.copyFileSync(homeBackup, homePath);
    fs.unlinkSync(homeBackup);
  }
  restoreRoutes();
}

console.log("Projector frontend build complete.");
