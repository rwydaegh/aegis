/**
 * Multi-angle contact sheet.
 *
 * A single camera angle hides whole classes of mistake - a surface turned away
 * from the source, a lobe aimed into the back half-space, an object floating -
 * all of which look fine head-on. This orbits the scene and writes one tile per
 * angle, so the build gets checked from several sides at once.
 *
 *   node contactsheet.mjs out-prefix [tileW] [tileH]
 */

import { chromium } from "playwright";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const prefix = process.argv[2] || resolve(here, "dist/angle");
const w = parseInt(process.argv[3] || "640", 10);
const h = parseInt(process.argv[4] || "400", 10);

// azimuth, elevation, radius, label
const VIEWS = [
  [28, 12, 9.5, "three-quarter"],
  [90, 10, 9.0, "side-on"],
  [152, 14, 9.5, "from-behind-panel"],
  [235, 16, 10.0, "reverse"],
  [40, 52, 11.0, "high"],
  [12, 2, 6.5, "eye-level-close"],
];

const browser = await chromium.launch({
  args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});
const page = await browser.newPage({ viewport: { width: w, height: h } });
const problems = [];
page.on("pageerror", (e) => problems.push(e.message));

await page.goto("file://" + resolve(here, "dist/test.html"), {
  waitUntil: "load",
  timeout: 90000,
});
await page.waitForTimeout(6000);

// Freeze the sweep so every tile shows the same beam state.
await page.evaluate(() => {
  document.getElementById("aim").value = "1.35";
  document.getElementById("aim").dispatchEvent(new Event("input"));
});
await page.waitForTimeout(1200);

for (const [az, el, r, label] of VIEWS) {
  await page.evaluate(
    ([a, e, rad]) => window.__studio.orbit(a, e, rad),
    [az, el, r]
  );
  await page.waitForTimeout(1400);
  const out = `${prefix}_${label}.png`;
  await page.screenshot({ path: out });
  console.log("wrote", out);
}

console.log("stats:", JSON.stringify(await page.evaluate(() => window.__studio.stats())));
if (problems.length) console.log("page errors:", problems.slice(0, 5));
await browser.close();
