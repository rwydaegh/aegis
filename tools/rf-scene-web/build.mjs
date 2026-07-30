/**
 * Bundle the scene into one self-contained HTML file.
 *
 * Published artifacts run under a CSP that blocks every external host, so
 * three.js, the addons and the phantom mesh all have to be inlined. esbuild
 * resolves and minifies the module graph into a single IIFE that we paste
 * into the shell.
 *
 *   node build.mjs
 *
 * Writes dist/artifact.html (body content only, for the Artifact tool) and
 * dist/test.html (a full document, for local screenshotting).
 */

import { build } from "esbuild";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dist = resolve(here, "dist");
mkdirSync(dist, { recursive: true });

const result = await build({
  entryPoints: [resolve(here, "src/main.js")],
  bundle: true,
  minify: true,
  format: "iife",
  target: ["chrome110", "firefox110", "safari16"],
  loader: { ".json": "json" },
  legalComments: "none",
  write: false,
});

const bundle = result.outputFiles[0].text;
const shell = readFileSync(resolve(here, "src/shell.html"), "utf8");

// The bundle is injected verbatim, so a literal </script> inside it would
// close the tag early. Nothing generates one today, but guard anyway.
const safe = bundle.replace(/<\/script>/gi, "<\\/script>");
const page = shell.replace("__BUNDLE__", () => safe);

writeFileSync(resolve(dist, "artifact.html"), page);
writeFileSync(
  resolve(dist, "test.html"),
  `<!doctype html><html><head><meta charset="utf-8">` +
    `<meta name="viewport" content="width=device-width,initial-scale=1">` +
    `</head><body>${page}</body></html>`
);

const kb = (Buffer.byteLength(page) / 1024).toFixed(0);
console.log(`bundle ${(Buffer.byteLength(bundle) / 1024).toFixed(0)} KB`);
console.log(`page   ${kb} KB -> dist/artifact.html, dist/test.html`);
