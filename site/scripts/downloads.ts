import { createHash } from "node:crypto";
import { lstat, readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { platforms, type Download } from "../src/lib/downloads.ts";

const fields = [
  "version",
  "os",
  "arch",
  "file",
  "bytes",
  "sha256",
  "sourceCommit",
  "prerelease",
  "releaseApproved",
  "native",
  "generation",
  "trust",
];
const extensions = {
  macos: ["dmg"],
  windows: ["exe", "msi"],
  linux: ["deb", "AppImage"],
};
const trust = {
  macos: ["macos-notarized", "macos-adhoc-blocked"],
  windows: ["windows-signed", "windows-unsigned"],
  linux: ["linux-unsigned"],
};
const semver =
  /^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))*)?$/;
const invalid = () =>
  new Error("Invalid download manifest; see DOWNLOAD-HANDOFF.md");

export async function stageDownloads(
  manifest: string | undefined,
  out: string,
): Promise<Download[]> {
  if (!manifest) return [];
  const data = JSON.parse(await readFile(manifest, "utf8"));
  if (
    !data ||
    Object.keys(data).join() !== "artifacts" ||
    !Array.isArray(data.artifacts)
  )
    throw invalid();
  const prepared: { download: Download; bytes: Buffer }[] = [];
  const seen = new Set<string>();
  const identities = new Map<string, string>();
  for (const item of data.artifacts) {
    if (
      !item ||
      typeof item !== "object" ||
      Array.isArray(item) ||
      Object.keys(item).some((key) => !fields.includes(key))
    )
      throw invalid();
    // A partial qualification remains unavailable, never a guessed default.
    if (fields.some((key) => item[key] === undefined)) continue;
    const d = item as Download;
    if (
      typeof d.version !== "string" ||
      !semver.test(d.version) ||
      !platforms.some((p) => p.os === d.os && p.arch === d.arch) ||
      !extensions[d.os].some(
        (ext) => d.file === `omr-${d.version}-${d.os}-${d.arch}.${ext}`,
      ) ||
      !Number.isSafeInteger(d.bytes) ||
      d.bytes <= 0 ||
      typeof d.sha256 !== "string" ||
      !/^[a-f0-9]{64}$/.test(d.sha256) ||
      typeof d.sourceCommit !== "string" ||
      !/^[a-f0-9]{40}$/.test(d.sourceCommit) ||
      (d.prerelease !== null && typeof d.prerelease !== "boolean") ||
      (d.version.includes("-") && d.prerelease !== true) ||
      typeof d.releaseApproved !== "boolean" ||
      !["verified", "unverified"].includes(d.native) ||
      !["verified", "synthetic-only"].includes(d.generation) ||
      !(d.trust === "unverified" || trust[d.os].includes(d.trust))
    )
      throw invalid();
    const currentIdentity = `${d.sourceCommit}:${d.prerelease}`;
    const identity = identities.get(d.version);
    if (identity !== undefined && identity !== currentIdentity) throw invalid();
    identities.set(d.version, currentIdentity);
    const href = `/downloads/${d.version}/${d.file}`;
    if (seen.has(href)) throw invalid();
    seen.add(href);
    if (
      !d.releaseApproved ||
      d.native !== "verified" ||
      ["unverified", "macos-adhoc-blocked"].includes(d.trust)
    )
      continue;
    const path = join(dirname(manifest), d.file);
    try {
      const stat = await lstat(path);
      if (!stat.isFile() || stat.size !== d.bytes) continue;
      const bytes = await readFile(path);
      if (
        bytes.length !== d.bytes ||
        createHash("sha256").update(bytes).digest("hex") !== d.sha256
      )
        continue;
      // Copy the same verified buffer, not a second read of a mutable source.
      prepared.push({ download: { ...d, href }, bytes });
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
  }
  // Validate the full manifest before writing any package.
  // Reject pre-existing files, including dangling symlinks, before writing.
  for (const { download: d } of prepared) {
    for (const dest of [join(out, d.href), join(out, `${d.href}.sha256`)]) {
      try {
        await lstat(dest);
        throw invalid();
      } catch (error) {
        if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
      }
    }
  }
  for (const { download: d, bytes } of prepared) {
    const dest = join(out, d.href);
    await mkdir(dirname(dest), { recursive: true });
    await writeFile(dest, bytes, { flag: "wx" });
    await writeFile(`${dest}.sha256`, `${d.sha256}  ${d.file}\n`, {
      flag: "wx",
    });
  }
  return prepared.map(({ download }) => download);
}
