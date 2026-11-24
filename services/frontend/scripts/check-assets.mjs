import assert from "node:assert/strict";
import { readFile, readdir, stat } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const dist = resolve(root, "dist");
const html = await readFile(resolve(dist, "index.html"), "utf8");
const references = [
  ...html.matchAll(/(?:src|href)="(\/assets\/[^"?#]+)"/g),
].map((match) => match[1]);
assert(
  references.some((path) => path.endsWith(".js")),
  "Built entry JavaScript missing",
);
assert(
  references.some((path) => path.endsWith(".css")),
  "Built entry stylesheet missing",
);
for (const path of references)
  assert(
    (await stat(resolve(dist, "." + path))).size > 0,
    `Empty asset: ${path}`,
  );
const assets = await readdir(resolve(dist, "assets"));
assert(
  assets.some((path) => /^aurora-logo-.*\.svg$/.test(path)),
  "Bundled Aurora logo missing",
);
async function checkPublic(folder, relative = "", entries = null) {
  for (const entry of entries ??
    (await readdir(folder, { withFileTypes: true }))) {
    const path = relative ? `${relative}/${entry.name}` : entry.name;
    if (entry.isDirectory())
      await checkPublic(resolve(folder, entry.name), path);
    else
      assert.deepEqual(
        await readFile(resolve(root, "public", path)),
        await readFile(resolve(dist, path)),
        `Public asset changed or missing: ${path}`,
      );
  }
}
const publicRoot = resolve(root, "public");
// Vite's public directory is optional; an empty one is absent in clean Git trees.
// Only this root enumeration may be missing. Nested reads, permissions, and all
// required dist assets retain their original failures.
let publicEntries;
try {
  publicEntries = await readdir(publicRoot, { withFileTypes: true });
} catch (error) {
  if (error.code !== "ENOENT" || error.path !== publicRoot) throw error;
  publicEntries = [];
}
await checkPublic(publicRoot, "", publicEntries);
console.log(
  `Built entry, ${references.length} references, logo and public assets verified.`,
);
