// Isolated plumbing fixture: never write synthetic packages into site/dist.
import {
  mkdtemp,
  cp,
  copyFile,
  symlink,
  writeFile,
  rm,
  readFile,
} from "node:fs/promises";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import assert from "node:assert/strict";

const site = resolve(import.meta.dirname, "..");
const root = await mkdtemp(join(tmpdir(), "omr-staging-test-"));
const defaultHTML = await readFile(join(site, "dist/index.html"));
const realReportPath = join(site, "artifacts/ready/browser/report.json");
const realReport = await readFile(realReportPath).catch((error) => {
  if (error.code !== "ENOENT") throw error;
  return undefined;
});
try {
  const isolated = join(root, "site");
  await cp(join(site, "src"), join(isolated, "src"), { recursive: true });
  for (const dir of ["scripts", "assets"])
    await cp(join(site, dir), join(isolated, dir), { recursive: true });
  for (const file of ["package.json", "tsconfig.json", "favicon.ico"])
    await copyFile(join(site, file), join(isolated, file));
  await symlink(
    join(site, "node_modules"),
    join(isolated, "node_modules"),
    "dir",
  );
  const bytes = Buffer.from(
    "SYNTHETIC DOWNLOAD TEST ONLY — NOT AN INSTALLER\n",
  );
  const artifacts = [];
  for (const [os, arch, ext, trust, native] of [
    ["linux", "x64", "AppImage", "linux-unsigned", "verified"],
    ["linux", "x64", "deb", "linux-unsigned", "verified"],
    ["macos", "arm64", "dmg", "macos-adhoc-blocked", "verified"],
    ["windows", "x64", "exe", "windows-unsigned", "unverified"],
  ]) {
    const file = `omr-0.1.0-test.1-${os}-${arch}.${ext}`;
    await writeFile(join(root, file), bytes);
    artifacts.push({
      version: "0.1.0-test.1",
      os,
      arch,
      file,
      bytes: bytes.length,
      sha256: createHash("sha256").update(bytes).digest("hex"),
      sourceCommit: "a".repeat(40),
      prerelease: true,
      releaseApproved: true,
      native,
      generation: "synthetic-only",
      trust,
    });
  }
  const manifest = join(root, "manifest.json");
  await writeFile(manifest, JSON.stringify({ artifacts }));
  execFileSync("npm", ["run", "build"], {
    cwd: isolated,
    env: { ...process.env, OMR_DOWNLOADS_MANIFEST: manifest },
    stdio: "inherit",
  });
  const built = join(isolated, "dist");
  const env = {
    ...process.env,
    OMR_TEST_BUILT_DIR: built,
    OMR_BROWSER_OUTPUT: join(root, "synthetic-browser"),
  };
  execFileSync("python3", ["-B", "../tests/test_landing.py", "--built"], {
    cwd: site,
    env,
    stdio: "inherit",
  });
  execFileSync(
    join(site, "node_modules/.bin/html-validate"),
    ["--config", join(site, ".htmlvalidate.json"), join(built, "index.html")],
    { cwd: site, env, stdio: "inherit" },
  );
  execFileSync("node", ["tests/ready-browser.mjs"], {
    cwd: site,
    env,
    stdio: "inherit",
  });
  // Rebuild the isolated site without its input: stale packages must disappear.
  const inactive = { ...process.env };
  delete inactive.OMR_DOWNLOADS_MANIFEST;
  execFileSync("npm", ["run", "build"], {
    cwd: isolated,
    env: inactive,
    stdio: "inherit",
  });
  execFileSync("python3", ["-B", "../tests/test_landing.py", "--built"], {
    cwd: site,
    env,
    stdio: "inherit",
  });
  assert.deepEqual(await readFile(join(site, "dist/index.html")), defaultHTML);
  execFileSync("node", ["tests/ready-browser.mjs"], {
    cwd: site,
    env: { ...env, OMR_BROWSER_OUTPUT: join(root, "empty-browser") },
    stdio: "inherit",
  });
  if (realReport)
    assert.deepEqual(
      await readFile(realReportPath),
      realReport,
      "Synthetic staging must not overwrite real candidate evidence",
    );
  console.log(
    "PASS isolated synthetic staging + stale-package cleanup; production dist untouched",
  );
} finally {
  await rm(root, { recursive: true, force: true });
}
