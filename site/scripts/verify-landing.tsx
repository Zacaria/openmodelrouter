import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { R15_SOURCE_DELTA_SHA256 } from "./r15-materials.ts";
import { join } from "node:path";

import { renderPage } from "./render-ready.ts";
import type { Download } from "../src/lib/downloads.ts";

const [manifest, payload] = process.argv.slice(2);
if (!manifest || !payload) throw new Error("Missing manifest or payload");
const data = JSON.parse(await readFile(manifest, "utf8"));
const downloads: Download[] = data.artifacts.map((d: Download) => ({
  ...d,
  href: `/downloads/${d.version}/${d.file}`,
}));

let r15Materials = false;
try {
  const bytes = await readFile(
    join(payload, "assets/materials/0.3.2/rebuild.tar"),
  );
  if (
    createHash("sha256").update(bytes).digest("hex") !== R15_SOURCE_DELTA_SHA256
  )
    throw new Error("R15 source delta differs");
  r15Materials = true;
} catch (error) {
  if (!(error instanceof Error && "code" in error && error.code === "ENOENT"))
    throw error;
}

for (const [path, lang] of [
  ["index.html", "en"],
  ["en/index.html", "en"],
  ["fr/index.html", "fr"],
] as const) {
  const actual = await readFile(join(payload, path), "utf8");
  if (actual !== renderPage(lang, downloads, r15Materials))
    throw new Error(`Landing mismatch: ${path}`);
}
