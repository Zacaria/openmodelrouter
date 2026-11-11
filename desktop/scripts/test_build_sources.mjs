// Exercise the real frontend producer without inheriting Git ignore rules.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import {
  cp,
  mkdir,
  mkdtemp,
  readFile,
  readdir,
  rm,
  symlink,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const scratch = await mkdtemp(join(tmpdir(), "omr-build-inputs-"));
try {
  for (const name of [
    "src",
    "public",
    "index.html",
    "vite.config.ts",
    "package.json",
  ]) {
    await cp(join(root, name), join(scratch, name), { recursive: true });
  }
  await symlink(
    join(root, "node_modules"),
    join(scratch, "node_modules"),
    "junction",
  );
  const build = async () => {
    execFileSync(
      process.execPath,
      [join(root, "node_modules/vite/bin/vite.js"), "build"],
      {
        cwd: scratch,
        timeout: 60000,
        stdio: "pipe",
      },
    );
    assert.deepEqual(
      await readFile(join(scratch, "dist/brand/app-128.png")),
      await readFile(join(root, "public/brand/app-128.png")),
      "The production bundle lost or changed the supplied brand asset",
    );
    const assets = join(scratch, "dist/assets");
    const files = (await readdir(assets))
      .filter((name) => /\.(css|js)$/.test(name))
      .sort();
    return Promise.all(
      files.map(async (name) => [
        name,
        createHash("sha256")
          .update(await readFile(join(assets, name)))
          .digest("hex"),
      ]),
    );
  };
  const clean = await build();
  await mkdir(join(scratch, "generated"));
  await writeFile(
    join(scratch, "generated/unrelated.html"),
    '<div class="bg-fuchsia-950 rotate-123 z-[9876]">Unrelated build fixture</div>',
  );
  const contaminated = await build();
  assert.deepEqual(
    contaminated,
    clean,
    "Sources outside the app changed the production JS/CSS",
  );
  console.log(
    "PASS: identical JS/CSS with foreign build sources and no Git ignore rules",
  );
} finally {
  await rm(scratch, { recursive: true, force: true });
}
