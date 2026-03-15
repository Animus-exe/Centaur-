import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const __dirname = path.dirname(url.fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const src = path.resolve(root, "node_modules", "cesium", "Build", "Cesium");
const dst = path.resolve(root, "public", "cesium");

function copyDir(srcDir, dstDir) {
  if (!fs.existsSync(srcDir)) throw new Error("Cesium build not found: " + srcDir);
  fs.mkdirSync(dstDir, { recursive: true });
  for (const entry of fs.readdirSync(srcDir, { withFileTypes: true })) {
    const s = path.join(srcDir, entry.name);
    const d = path.join(dstDir, entry.name);
    if (entry.isDirectory()) copyDir(s, d);
    else fs.copyFileSync(s, d);
  }
}

try {
  if (fs.existsSync(dst)) fs.rmSync(dst, { recursive: true, force: true });
  copyDir(src, dst);
  console.log("[postinstall] Cesium assets copied to public/cesium");
} catch (e) {
  console.warn("[postinstall] Cesium copy failed:", e.message);
  process.exit(0);
}
