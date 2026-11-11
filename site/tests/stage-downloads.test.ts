import assert from "node:assert/strict";
import { test } from "node:test";
import { createHash } from "node:crypto";
import {
  mkdtemp,
  writeFile,
  readFile,
  readdir,
  symlink,
  rm,
  mkdir,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { stageDownloads } from "../scripts/downloads.ts";
import { renderPage } from "../scripts/render-ready.ts";

const bytes = Buffer.from("SYNTHETIC DOWNLOAD TEST ONLY — NOT AN INSTALLER\n");
const entry = {
  version: "0.1.0-test.1",
  os: "linux",
  arch: "x64",
  file: "omr-0.1.0-test.1-linux-x64.AppImage",
  bytes: bytes.length,
  sha256: createHash("sha256").update(bytes).digest("hex"),
  sourceCommit: "a".repeat(40),
  prerelease: true,
  releaseApproved: true,
  native: "verified",
  generation: "synthetic-only",
  trust: "linux-unsigned",
};
async function fixture(run: (root: string, out: string) => Promise<void>) {
  const root = await mkdtemp(join(tmpdir(), "omr-download-test-"));
  try {
    const out = join(root, "out");
    await mkdir(out);
    await writeFile(join(root, entry.file), bytes);
    await run(root, out);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
}
async function stage(root: string, out: string, artifacts: unknown[]) {
  const manifest = join(root, "manifest.json");
  await writeFile(manifest, JSON.stringify({ artifacts }));
  return stageDownloads(manifest, out);
}

test("no input, partial qualification, absent/tampered bytes and blocked trust remain unavailable", async () => {
  for (const patch of [
    { releaseApproved: false },
    { native: "unverified" },
    { trust: "unverified" },
    { bytes: bytes.length + 1 },
    { sha256: "0".repeat(64) },
    { prerelease: undefined },
    { generation: undefined },
    { sourceCommit: undefined },
    {
      os: "macos",
      file: "omr-0.1.0-test.1-macos-x64.dmg",
      trust: "macos-adhoc-blocked",
    },
  ]) {
    await fixture(async (root, out) => {
      assert.deepEqual(await stage(root, out, [{ ...entry, ...patch }]), []);
      assert.deepEqual(await readdir(out), []);
    });
  }
  await fixture(async (root, out) => {
    assert.deepEqual(await stageDownloads(undefined, out), []);
    await rm(join(root, entry.file));
    assert.deepEqual(await stage(root, out, [entry]), []);
    for (const lang of ["en", "fr"] as const) {
      const html = renderPage(lang, []);
      assert.ok(!html.includes('href="/downloads/'));
      assert.ok(!html.includes("v0.1.0"), "No stale snapshot version");
    }
  });
});

test("a numeric package with no GitHub status renders without inventing one", async () => {
  await fixture(async (root, out) => {
    const item = {
      ...entry,
      version: "0.3.2",
      file: "omr-0.3.2-linux-x64.AppImage",
      prerelease: null,
    };
    await writeFile(join(root, item.file), bytes);
    const downloads = await stage(root, out, [item]);
    assert.equal(downloads.length, 1);
    for (const lang of ["en", "fr"] as const) {
      const html = renderPage(lang, downloads);
      const data = JSON.parse(
        html.match(
          /<script id="release-data" type="application\/json">(.*?)<\/script>/s,
        )![1],
      );
      assert.equal(data.packages[0].prerelease, null);
      assert.equal(data.packages[0].notes, "");
    }
  });
  await fixture(async (root, out) => {
    await assert.rejects(stage(root, out, [{ ...entry, prerelease: null }]));
  });
});

test("exact verified bytes, sidecars and actual release data reach both locales", async () => {
  await fixture(async (root, out) => {
    const downloads = await stage(root, out, [entry]);
    assert.equal(downloads.length, 1);
    const d = downloads[0];
    assert.deepEqual(await readFile(join(out, d.href)), bytes);
    assert.equal(
      await readFile(join(out, `${d.href}.sha256`), "utf8"),
      `${entry.sha256}  ${entry.file}\n`,
    );
    for (const lang of ["en", "fr"] as const) {
      const html = renderPage(lang, downloads);
      for (const value of [
        d.href,
        `${d.href}.sha256`,
        d.sha256,
        d.sourceCommit,
        "AppImage",
        lang === "fr" ? "Préversion" : "Prerelease",
      ])
        assert.ok(html.includes(value), value);
      assert.ok(!html.includes("backend synthétique"));
      assert.ok(!html.includes("synthetic-only"));
      assert.ok(!html.includes("releaseApproved"));
    }
  });
});

test("mixed platform releases retain each package version and source in both locales", async () => {
  await fixture(async (root, out) => {
    const arm = {
      ...entry,
      version: "0.3.0",
      os: "macos",
      arch: "arm64",
      file: "omr-0.3.0-macos-arm64.dmg",
      sourceCommit: "b".repeat(40),
      trust: "macos-notarized",
    };
    await writeFile(join(root, arm.file), bytes);
    const downloads = await stage(root, out, [arm, entry]);
    assert.equal(downloads.length, 2);
    for (const lang of ["en", "fr"] as const) {
      const html = renderPage(lang, downloads);
      const data = JSON.parse(
        html.match(
          /<script id="release-data" type="application\/json">(.*?)<\/script>/s,
        )![1],
      );
      assert.equal("version" in data, false);
      assert.equal("commit" in data, false);
      assert.deepEqual(
        data.packages.map((d: { version: string; sourceCommit: string }) => [
          d.version,
          d.sourceCommit,
        ]),
        [
          [arm.version, arm.sourceCommit],
          [entry.version, entry.sourceCommit],
        ],
      );
      assert.match(html, /Apple Silicon<\/strong><span>v0\.3\.0/);
      assert.match(html, /Linux · x64<\/strong><span>v0\.1\.0-test\.1/);
    }
    for (const download of downloads)
      assert.deepEqual(await readFile(join(out, download.href)), bytes);
  });
});

test("empty, partial and complete manifests expose only admitted platforms and correct trust", async () => {
  await fixture(async (root, out) => {
    const entries = [
      {
        ...entry,
        os: "macos",
        arch: "arm64",
        file: `omr-${entry.version}-macos-arm64.dmg`,
        trust: "macos-notarized",
      },
      {
        ...entry,
        os: "macos",
        arch: "x64",
        file: `omr-${entry.version}-macos-x64.dmg`,
        trust: "macos-notarized",
      },
      {
        ...entry,
        os: "windows",
        file: `omr-${entry.version}-windows-x64.exe`,
        trust: "windows-unsigned",
      },
      entry,
    ];
    for (const item of entries) await writeFile(join(root, item.file), bytes);
    for (const count of [0, 2, 4]) {
      const dest = join(out, String(count));
      await mkdir(dest);
      const ds = await stage(root, dest, entries.slice(0, count));
      for (const lang of ["en", "fr"] as const) {
        const html = renderPage(lang, ds);
        const data = JSON.parse(
          html.match(
            /<script id="release-data" type="application\/json">(.*?)<\/script>/s,
          )![1],
        );
        assert.equal(data.packages.length, count);
        for (const item of ds) assert.ok(html.includes(`href="${item.href}"`));
        assert.equal(
          html.includes(
            lang === "fr" ? "avertissement de sécurité" : "security warning",
          ),
          count === 4,
        );
      }
    }
  });
});

test("multiple formats survive without invented architecture or filename", async () => {
  await fixture(async (root, out) => {
    const deb = { ...entry, file: `omr-${entry.version}-linux-x64.deb` };
    await writeFile(join(root, deb.file), bytes);
    const ds = await stage(root, out, [entry, deb]);
    assert.equal(ds.length, 2);
    for (const d of ds) assert.ok(renderPage("en", ds).includes(d.href));
  });
});

test("rejects invalid SemVer, release status, metadata, names, duplicate/mixed identities and collisions", async () => {
  const patches = [
    { version: "01.1.0" },
    { version: "1.0.0-01" },
    { version: "1.0.0-a..b" },
    { prerelease: false },
    { file: "../private.zip" },
    { file: "https://github.com/private/file" },
    { file: "omr-0.1.0-test.1-linux-x64.zip" },
    { sourceCommit: "https://github.com/private" },
    { sourceUrl: "private-token" },
    { trust: "windows-signed" },
  ];
  for (const patch of patches)
    await fixture(async (root, out) => {
      await assert.rejects(stage(root, out, [{ ...entry, ...patch }]));
      assert.deepEqual(await readdir(out), []);
    });
  await fixture(async (root, out) => {
    await assert.rejects(stage(root, out, [entry, entry]));
    const other = {
      ...entry,
      os: "windows",
      file: `omr-${entry.version}-windows-x64.exe`,
      trust: "windows-unsigned",
      sourceCommit: "b".repeat(40),
    };
    await assert.rejects(stage(root, out, [entry, other]));
    assert.deepEqual(await readdir(out), []);
    await stage(root, out, [entry]);
    await assert.rejects(stage(root, out, [entry]));
    assert.deepEqual(
      await readFile(join(out, "downloads", entry.version, entry.file)),
      bytes,
    );
  });
});

test("a numeric version rejects contradictory release status before copying any package", async () => {
  for (const prerelease of [true, false]) {
    await fixture(async (root, out) => {
      const first = {
        ...entry,
        version: "0.3.0",
        file: "omr-0.3.0-linux-x64.AppImage",
        prerelease,
      };
      const second = {
        ...first,
        os: "windows",
        file: "omr-0.3.0-windows-x64.exe",
        trust: "windows-unsigned",
        prerelease: !prerelease,
      };
      for (const [index, item] of [first, second].entries()) {
        await writeFile(join(root, item.file), bytes);
        assert.equal(
          (await stage(root, join(root, `individual-${index}`), [item])).length,
          1,
        );
      }
      await assert.rejects(stage(root, out, [first, second]));
      assert.deepEqual(await readdir(out), []);
    });
  }
});

test("malformed manifests and symlink payloads fail closed", async () => {
  for (const json of [
    "{",
    "null",
    "[]",
    '{"artifacts":null}',
    '{"artifacts":[],"private":"secret"}',
    '{"artifacts":[null]}',
  ]) {
    await fixture(async (root, out) => {
      const manifest = join(root, "manifest.json");
      await writeFile(manifest, json);
      await assert.rejects(stageDownloads(manifest, out));
      assert.deepEqual(await readdir(out), []);
    });
  }
  await fixture(async (root, out) => {
    await rm(join(root, entry.file));
    await writeFile(join(root, "private.txt"), bytes);
    await symlink(join(root, "private.txt"), join(root, entry.file));
    assert.deepEqual(await stage(root, out, [entry]), []);
    assert.deepEqual(await readdir(out), []);
  });
});
