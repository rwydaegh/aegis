/**
 * Screenshot the built page so the scene can be iterated on without a browser.
 *
 *   node shot.mjs out.png [width] [height] [waitMs]
 *
 * WebGL in headless Chromium runs on SwiftShader, so this is slow but it does
 * exercise the real shader path - if a shader fails to compile it shows up
 * here rather than after publishing.
 */

import { chromium } from "playwright";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const out = process.argv[2] || resolve(here, "dist/shot.png");
const width = parseInt(process.argv[3] || "1280", 10);
const height = parseInt(process.argv[4] || "720", 10);
const waitMs = parseInt(process.argv[5] || "6000", 10);

const browser = await chromium.launch({
  args: [
    "--use-gl=angle",
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
    "--ignore-gpu-blocklist",
  ],
});
const page = await browser.newPage({ viewport: { width, height } });

const problems = [];
page.on("console", (m) => {
  if (m.type() === "error" || m.type() === "warning") {
    problems.push(`[${m.type()}] ${m.text()}`);
  }
});
page.on("pageerror", (e) => problems.push(`[pageerror] ${e.message}`));

await page.goto("file://" + resolve(here, "dist/test.html"), {
  waitUntil: "load",
  timeout: 90000,
});
await page.waitForTimeout(waitMs);

// Pull the live HUD values back out, so the run reports numbers and not just
// an image.
const readout = await page.evaluate(() => {
  const t = (id) => (document.getElementById(id) || {}).textContent || "?";
  const canvas = document.querySelector("canvas");
  return {
    eirp: t("eirp"),
    scan: t("scan"),
    dist: t("dist"),
    sab: t("sab"),
    limit: t("limit"),
    canvas: canvas ? `${canvas.width}x${canvas.height}` : "MISSING",
  };
});

await page.screenshot({ path: out });
await browser.close();

console.log("readout:", JSON.stringify(readout));
if (problems.length) {
  console.log("console problems:");
  for (const p of problems.slice(0, 15)) console.log("  " + p);
} else {
  console.log("no console errors");
}
console.log("wrote", out);
