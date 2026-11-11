import { readFileSync } from "node:fs";
import type { Download } from "../src/lib/downloads.ts";

export type Language = "en" | "fr";
const templates = Object.fromEntries(
  ["en", "fr"].map((lang) => [
    lang,
    readFileSync(
      new URL(`../src/templates/${lang}.html`, import.meta.url),
      "utf8",
    )
      .replaceAll('hidden=""', "hidden")
      .replaceAll('href=""', 'href="#main"')
      .replace("<script defer src=", '<script defer="" src=')
      .replace(/<button(?![^>]*\btype=)/g, '<button type="button"')
      .replace(
        /<div\s+aria-label="([^"]+)"\s+class="(download-panel|package-options)"/g,
        '<div role="group" aria-label="$1" class="$2"',
      )
      .replace(
        '<div class="package-table" role="list">',
        '<ul class="package-table">',
      )
      .replace("<!--packages--></div>", "<!--packages--></ul>"),
  ]),
);
const escapeHTML = (text: string) =>
  text.replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ]!,
  );

export function renderPage(
  lang: Language,
  downloads: Download[],
  r15Materials = false,
) {
  const fr = lang === "fr";
  const labels = { macos: "macOS", windows: "Windows", linux: "Linux" };
  const unavailable = fr ? "Aucun paquet disponible." : "No package available.";
  const versions = new Set(downloads.map((d) => d.version));
  const version = versions.size === 1 ? downloads[0]?.version : undefined;
  const versionLabel = version
    ? `v${version}`
    : downloads.length
      ? fr
        ? "Installateurs"
        : "Installers"
      : "—";
  const release = {
    packages: downloads.map((d) => ({
      version: d.version,
      sourceCommit: d.sourceCommit,
      os: d.os,
      arch: d.arch,
      format: d.file.split(".").at(-1),
      bytes: d.bytes,
      file: d.file,
      sha256: d.sha256,
      prerelease: d.prerelease,
      url: d.href,
      checksumUrl: `${d.href}.sha256`,
      notes: [
        d.prerelease ? (fr ? "Préversion" : "Prerelease") : "",
        d.trust === "windows-unsigned"
          ? fr
            ? "Windows peut afficher un avertissement de sécurité : cet installateur n’est pas signé."
            : "Windows may show a security warning: this installer is not signed."
          : "",
      ]
        .filter(Boolean)
        .join(" · "),
    })),
  };
  const rows =
    release.packages
      .map((d) => {
        const arch =
          d.os === "macos"
            ? d.arch === "arm64"
              ? "Apple Silicon"
              : "Intel"
            : d.arch;
        return `<li><strong>${labels[d.os]} · ${arch}</strong><span>v${escapeHTML(d.version)} · .${d.format} · ${(d.bytes / 1e6).toLocaleString(lang, { maximumFractionDigits: 1, minimumFractionDigits: 1 })} MB</span><a href="${d.url}" download="${d.file}">${fr ? "Télécharger" : "Download"}</a><a href="${d.checksumUrl}">SHA-256</a><p class="package-notes">${escapeHTML(d.notes)}</p></li>`;
      })
      .join("") || `<li><p>${unavailable}</p></li>`;
  return (
    templates[lang]
      .replace(
        "<!--release-data-->",
        JSON.stringify(release).replace(/</g, "\\u003c"),
      )
      .replace("<!--packages-->", rows)
      .replace(
        "          <!--r15-materials-->",
        r15Materials
          ? `          <a href="/assets/materials/0.3.2/">${fr ? "Sources du moteur" : "Engine sources"} · 0.3.2 ARM64</a>`
          : "",
      )
      .replaceAll("<!--version-->", escapeHTML(versionLabel))
      // The export snapshot has a fixed releaseMeta in its localized UI catalogue.
      .replace(
        /"releaseMeta":\s*"[^"]*"/,
        `"releaseMeta":${JSON.stringify(downloads.length ? versionLabel : unavailable)}`,
      )
  );
}
