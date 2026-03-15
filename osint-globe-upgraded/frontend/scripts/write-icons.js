import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const __dirname = path.dirname(url.fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const pub = path.resolve(root, "public");

fs.mkdirSync(pub, { recursive: true });

const icons = {
  "plane.svg": `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="gPlane" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#9ed0ff" />
      <stop offset="100%" stop-color="#4f9cff" />
    </linearGradient>
  </defs>
  <circle cx="32" cy="32" r="30" fill="rgba(8, 15, 26, 0.88)" stroke="#4f9cff" stroke-width="2"/>
  <path d="M32 8l7 15 17 6-17 6-7 21-7-21-17-6 17-6z" fill="url(#gPlane)"/>
</svg>`,
  "area.svg": `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <circle cx="32" cy="24" r="18" fill="#ff8a9a" />
  <path d="M32 62L17 34h30z" fill="#ff5f75" />
  <circle cx="32" cy="24" r="8" fill="#ffd6dc" />
</svg>`,
  "fuel.svg": `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect x="12" y="10" width="30" height="44" rx="6" fill="#ffd574" />
  <rect x="18" y="18" width="18" height="12" rx="2" fill="#3a2d10" />
  <path d="M42 18h8l4 8v16a6 6 0 01-6 6h-2z" fill="#ffbe3f" />
  <circle cx="27" cy="40" r="7" fill="#3a2d10" />
</svg>`
};

for (const [name, svg] of Object.entries(icons)) {
  const out = path.resolve(pub, name);
  fs.writeFileSync(out, svg);
}

console.log("[postinstall] Marker icons written to public/");
