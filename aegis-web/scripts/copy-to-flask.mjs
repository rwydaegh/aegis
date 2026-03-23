/**
 * Copy Vite output (dist/) into the Flask package so GET / serves the React app.
 * See src/aegis/viewer/routes/data.py (static/index.html).
 */
import { cpSync, existsSync, rmSync } from "fs"
import { dirname, join } from "path"
import { fileURLToPath } from "url"

const __dirname = dirname(fileURLToPath(import.meta.url))
const webRoot = join(__dirname, "..")
const dist = join(webRoot, "dist")
const target = join(webRoot, "..", "src", "aegis", "viewer", "static")

if (!existsSync(dist)) {
  console.error("dist/ not found. Run npm run build first.")
  process.exit(1)
}
rmSync(target, { recursive: true, force: true })
cpSync(dist, target, { recursive: true })
console.log(`Copied React build to ${target}`)
