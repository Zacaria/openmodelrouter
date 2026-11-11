import { test } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { stageR15Materials } from "../scripts/r15-materials.ts";
import { renderPage } from "../scripts/render-ready.ts";

test("source links appear only when the archive was staged", () => {
  for (const lang of ["en", "fr"] as const) {
    assert.doesNotMatch(
      renderPage(lang, [], false),
      /assets\/materials\/0\.3\.2\//,
    );
    assert.match(renderPage(lang, [], true), /assets\/materials\/0\.3\.2\//);
  }
});

test("stage only the exact selected source archive", async () => {
  const root = await mkdtemp(join(tmpdir(), "omr-r15-materials-"));
  try {
    const source = join(root, "source.tar");
    const output = join(root, "out");
    const bytes = Buffer.from("synthetic source fixture");
    const hash = createHash("sha256").update(bytes).digest("hex");
    assert.equal(await stageR15Materials(undefined, output, hash), false);
    await writeFile(source, bytes);
    assert.equal(await stageR15Materials(source, output, hash), true);
    assert.deepEqual(
      await readFile(join(output, "assets/materials/0.3.2/rebuild.tar")),
      bytes,
    );
    await assert.rejects(stageR15Materials(source, output, hash));
    assert.deepEqual(
      await readFile(join(output, "assets/materials/0.3.2/rebuild.tar")),
      bytes,
    );
    await writeFile(source, Buffer.from("changed fixture"));
    await assert.rejects(stageR15Materials(source, join(root, "bad"), hash));
    await assert.rejects(
      readFile(join(root, "bad/assets/materials/0.3.2/rebuild.tar")),
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
