import { chromium } from "@playwright/test";
import { createServer } from "node:http";
import { readFile, mkdtemp, rm } from "node:fs/promises";
import { resolve, join, dirname } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import assert from "node:assert/strict";
import { R15_SOURCE_DELTA_SHA256 } from "../scripts/r15-materials.ts";

const site = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const root = resolve(process.env.OMR_TEST_BUILT_DIR || join(site, "dist"));
const server = createServer(async (req, res) => {
  try {
    const path = decodeURIComponent(
      new URL(req.url, "http://localhost").pathname,
    );
    // Exercise a host that serves the index without redirecting the URL.
    const target =
      path === "/assets/materials/0.3.2"
        ? path + "/index.html"
        : path.endsWith("/")
          ? path + "index.html"
          : path;
    const file = resolve(root, "." + target);
    if (!file.startsWith(root + "/")) return res.writeHead(403).end();
    const bytes = await readFile(file);
    res.setHeader(
      "Content-Type",
      file.endsWith(".html")
        ? "text/html; charset=utf-8"
        : "application/octet-stream",
    );
    res.end(bytes);
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise((done) => server.listen(0, "127.0.0.1", done));
const tmp = await mkdtemp(join(tmpdir(), "omr-r15-browser-"));
let browser;
try {
  browser = await chromium.launch({
    executablePath: process.env.BROWSER_PATH || "/usr/bin/brave-browser",
    headless: true,
    chromiumSandbox: true,
  });
  const context = await browser.newContext({
    acceptDownloads: true,
    viewport: { width: 320, height: 800 },
  });
  for (const lang of ["en", "fr"]) {
    const page = await context.newPage();
    await page.goto(`http://127.0.0.1:${server.address().port}/${lang}/`);
    const source = page.locator('a[href="/assets/materials/0.3.2/"]');
    assert.equal(await source.count(), 1);
    assert.equal(await page.locator('a[href*="github.com"]').count(), 0);
    await source.click();
    assert.equal(new URL(page.url()).pathname, "/assets/materials/0.3.2/");
    const dimensions = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      content: document.documentElement.scrollWidth,
    }));
    assert.ok(
      dimensions.content <= dimensions.viewport,
      `source page overflows at ${dimensions.viewport}px`,
    );
    const href = await page
      .locator('a[href="/assets/materials/0.3.2/rebuild.tar"]')
      .getAttribute("href");
    assert.equal(
      new URL(href!, "http://localhost/assets/materials/0.3.2").pathname,
      "/assets/materials/0.3.2/rebuild.tar",
    );
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.locator('a[href="/assets/materials/0.3.2/rebuild.tar"]').click(),
    ]);
    const path = join(tmp, `${lang}.tar`);
    await download.saveAs(path);
    assert.equal(
      createHash("sha256")
        .update(await readFile(path))
        .digest("hex"),
      R15_SOURCE_DELTA_SHA256,
    );
    await page.goto(
      `http://127.0.0.1:${server.address().port}/assets/materials/0.3.2`,
    );
    assert.equal(new URL(page.url()).pathname, "/assets/materials/0.3.2");
    const directLink = page.locator(
      'a[href="/assets/materials/0.3.2/rebuild.tar"]',
    );
    assert.equal(await directLink.count(), 1);
    const [directDownload] = await Promise.all([
      page.waitForEvent("download"),
      directLink.click(),
    ]);
    const directPath = join(tmp, `${lang}-direct.tar`);
    await directDownload.saveAs(directPath);
    assert.equal(
      createHash("sha256")
        .update(await readFile(directPath))
        .digest("hex"),
      R15_SOURCE_DELTA_SHA256,
    );
    await page.close();
    console.log(`${lang}: source route and exact download PASS`);
  }
  await context.close();
} finally {
  if (browser) await browser.close();
  await new Promise((done) => server.close(done));
  await rm(tmp, { recursive: true, force: true });
}
