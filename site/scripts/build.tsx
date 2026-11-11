import { mkdir, writeFile, copyFile, cp, rm } from "node:fs/promises";
import { constants } from "node:fs";
import { fileURLToPath } from "node:url";
import { renderPage } from "./render-ready.ts";
import { stageDownloads } from "./downloads.ts";
import { stageR15Materials } from "./r15-materials.ts";

process.chdir(fileURLToPath(new URL("..", import.meta.url)));

// Rebuild only this generated directory; never leak reference sources or stale files.
await rm("dist", { recursive: true, force: true });
await mkdir("dist", { recursive: true });
const downloads = await stageDownloads(
  process.env.OMR_DOWNLOADS_MANIFEST,
  "dist",
);
await cp("assets", "dist/assets", { recursive: true });
const r15Materials = await stageR15Materials(
  process.env.OMR_R15_SOURCE_DELTA,
  "dist",
);
if (r15Materials) {
  await copyFile(
    "src/r15-materials.html",
    "dist/assets/materials/0.3.2/index.html",
    constants.COPYFILE_EXCL,
  );
}
for (const lang of ["en", "fr"] as const) {
  const html = renderPage(lang, downloads, r15Materials);
  await mkdir(`dist/${lang}`, { recursive: true });
  await writeFile(`dist/${lang}/index.html`, html);
  if (lang === "en") await writeFile("dist/index.html", html);
}
await copyFile("src/language-routing.js", "dist/language-routing.js");
await copyFile("src/ready.mjs", "dist/landing.mjs");
await copyFile("src/ready.css", "dist/styles.css");
await copyFile("favicon.ico", "dist/favicon.ico");
console.log("Prerendered /, /en/ and /fr/");
