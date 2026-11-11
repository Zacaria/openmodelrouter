import { chromium } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { createServer } from "node:http";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { resolve, extname, join } from "node:path";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";

const site = resolve(fileURLToPath(new URL("..", import.meta.url)));
const root = resolve(process.env.OMR_TEST_BUILT_DIR || join(site, "dist"));
const output = resolve(
  process.env.OMR_BROWSER_OUTPUT || join(site, "artifacts/ready/browser"),
);
await mkdir(output, { recursive: true });
let server;
let origin = process.env.OMR_TEST_ORIGIN?.replace(/\/$/, "");
if (!origin) {
  server = createServer(async (req, res) => {
    try {
      const path = decodeURIComponent(
        new URL(req.url, "http://localhost").pathname,
      );
      const file = resolve(
        root,
        "." + (path.endsWith("/") ? path + "index.html" : path),
      );
      if (!file.startsWith(root + "/")) return res.writeHead(403).end();
      const data = await readFile(file);
      res.setHeader(
        "Content-Type",
        {
          ".html": "text/html; charset=utf-8",
          ".js": "text/javascript",
          ".mjs": "text/javascript",
          ".css": "text/css",
          ".json": "application/json",
          ".webp": "image/webp",
          ".png": "image/png",
          ".svg": "image/svg+xml",
          ".woff2": "font/woff2",
          ".ico": "image/x-icon",
        }[extname(file)] || "application/octet-stream",
      );
      res.end(data);
    } catch {
      res.writeHead(404).end();
    }
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  origin = `http://127.0.0.1:${server.address().port}`;
}
const report = {
  layouts: [],
  scenarios: [],
  detection: [],
  screenshots: [],
  axe: [],
  errors: [],
  skipped: [],
};
let browser;
const watch = (page) => {
  page.on("pageerror", (e) => report.errors.push(`pageerror: ${e.message}`));
  page.on("console", (e) => {
    if (e.type() === "error") report.errors.push(`console: ${e.text()}`);
  });
  page.on("request", (r) => {
    if (new URL(r.url()).origin !== new URL(origin).origin)
      report.errors.push(`external request: ${r.url()}`);
  });
  page.on("requestfailed", (r) =>
    report.errors.push(`request failed: ${r.url()} ${r.failure()?.errorText}`),
  );
  page.on("response", (r) => {
    if (r.status() >= 400) report.errors.push(`HTTP ${r.status()}: ${r.url()}`);
  });
};
const setup = async (context) =>
  context.addInitScript(() => {
    Object.defineProperty(navigator, "platform", { value: "MacIntel" });
    Object.defineProperty(navigator, "userAgent", {
      value: "Mozilla/5.0 (Macintosh; Intel Mac OS X)",
    });
    Object.defineProperty(navigator, "maxTouchPoints", { value: 0 });
    Object.defineProperty(navigator, "userAgentData", { value: undefined });
  });
const url = (lang) => `${origin}/${lang}/`;
const screenshot = async (page, name) => {
  await page.screenshot({ path: join(output, `${name}.png`) });
  report.screenshots.push(name);
};
const ctas = (page) => page.locator("[data-download] .download-cta");
async function checkDownloads(page, release) {
  const state = await page.evaluate(() => window.OMR.getState());
  const hrefs = await ctas(page).evaluateAll((els) =>
    els.map((el) => el.getAttribute("href")),
  );
  assert.equal(hrefs.length, 2);
  assert.equal(hrefs[0], hrefs[1], "download panels must agree");
  const matches = release.packages.filter(
    (p) => p.os === state.os && p.arch === state.arch,
  );
  if (hrefs[0]) {
    const pkg = matches.find(
      (p) =>
        new URL(p.url, locationOrigin(page)).href ===
        new URL(hrefs[0], locationOrigin(page)).href,
    );
    assert.ok(pkg, `download does not match manifest: ${hrefs[0]}`);
    for (const text of await page
      .locator("[data-download] .package-meta")
      .allTextContents())
      assert.ok(
        text.startsWith(`v${pkg.version} ·`),
        `Wrong package version: ${text}`,
      );
    assert.ok(
      (await page.locator(".package-facts").textContent()).startsWith(
        `v${pkg.version} ·`,
      ),
    );
    assert.equal(
      await page.locator(".source-commit code").textContent(),
      pkg.sourceCommit,
    );
  } else {
    assert.equal(
      await ctas(page)
        .filter({ has: page.locator("span") })
        .count(),
      2,
    );
    assert.deepEqual(
      await ctas(page).evaluateAll((els) =>
        els.map((el) => el.getAttribute("aria-disabled")),
      ),
      ["true", "true"],
    );
    if (matches.length)
      assert.fail("matching package exists but downloads are disabled");
  }
}
const locationOrigin = (page) => new URL(page.url()).origin;
async function assertScenario(page, scenario) {
  assert.deepEqual(
    await page
      .locator("[data-route].active")
      .evaluateAll((es) => es.map((e) => e.dataset.route)),
    [scenario.key],
  );
  assert.equal(
    await page
      .locator('.scenario-options [aria-pressed="true"]')
      .getAttribute("data-scenario"),
    scenario.key,
  );
  assert.equal(
    await page.locator("[data-request]").innerText(),
    `“${scenario.request}”`,
  );
  assert.equal(
    await page.locator("[data-short-family]").innerText(),
    scenario.short,
  );
  assert.equal(
    (await page.evaluate(() => window.OMR.getState())).scenario,
    scenario.key,
  );
}
try {
  browser = await chromium.launch({
    executablePath: process.env.BROWSER_PATH || "/usr/bin/brave-browser",
    headless: true,
    chromiumSandbox: true,
  });
  report.browser = browser.version();
  for (const lang of ["en", "fr"]) {
    const context = await browser.newContext({
      viewport: { width: 390, height: 900 },
      reducedMotion: "reduce",
    });
    await setup(context);
    const page = await context.newPage();
    watch(page);
    for (const width of [320, 390, 768, 1280, 1534]) {
      await page.setViewportSize({ width, height: 900 });
      if (page.url() !== "about:blank")
        await page.evaluate(() => localStorage.clear());
      await page.goto(url(lang), { waitUntil: "networkidle" });
      await page.evaluate(() => document.fonts.ready);
      assert.equal(await page.locator("html").getAttribute("lang"), lang);
      assert.equal(
        await page
          .locator(
            '.footer-bottom a[href="https://open-model-router-materials-3.vercel.app/"]',
          )
          .isVisible(),
        true,
        `${lang}/${width} source materials link is hidden`,
      );
      assert.equal(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        true,
        `${lang}/${width} horizontal overflow`,
      );
      assert.deepEqual(
        await page
          .locator("img")
          .evaluateAll((es) =>
            es
              .filter((e) => !e.complete || e.naturalWidth === 0)
              .map((e) => e.src),
          ),
        [],
        "broken images",
      );
      assert.equal(
        await page
          .locator('[data-download="hero"], [data-download="footer"]')
          .count(),
        2,
      );
      assert.deepEqual(
        await ctas(page).evaluateAll((es) =>
          es.map((e) => e.getAttribute("href")),
        ),
        [null, null],
        "generic Mac chip must not be inferred",
      );
      const scenarios = await page
        .locator("#scenario-data")
        .evaluate((el) => JSON.parse(el.textContent));
      assert.deepEqual(
        scenarios.map((s) => s.key),
        ["quick", "chat", "reason", "vision"],
      );
      assert.equal(
        await page.locator(".scenario-options [data-scenario]").count(),
        4,
      );
      for (const scenario of scenarios) {
        await page
          .locator(`.scenario-options [data-scenario="${scenario.key}"]`)
          .click();
        await assertScenario(page, scenario);
        report.scenarios.push(`${lang}/${width}/${scenario.key}`);
      }
      const options = page.locator(".scenario-options [data-scenario]");
      await options.first().focus();
      for (const [key, index] of [
        ["End", 3],
        ["Home", 0],
        ["ArrowRight", 1],
        ["ArrowLeft", 0],
        ["ArrowDown", 1],
        ["ArrowUp", 0],
      ]) {
        await page.keyboard.press(key);
        assert.equal(
          await options
            .nth(index)
            .evaluate((el) => document.activeElement === el),
          true,
          `${key} focus`,
        );
        await assertScenario(page, scenarios[index]);
      }
      await options.nth(2).focus();
      await page.keyboard.press("Enter");
      await assertScenario(page, scenarios[2]);
      const release = await page.evaluate(() => window.OMR.getRelease());
      assert.ok(
        Array.isArray(release.packages),
        "release manifest packages missing",
      );
      for (const os of ["macos", "windows", "linux"]) {
        await page.locator(`[data-download="hero"] [data-os="${os}"]`).click();
        assert.equal(
          await page
            .locator(`[data-download] [data-os="${os}"][aria-pressed="true"]`)
            .count(),
          2,
        );
        await checkDownloads(page, release);
        const arches = await page
          .locator('[data-download="hero"] .package-options [data-arch]')
          .evaluateAll((es) => es.map((e) => e.dataset.arch));
        for (const arch of arches) {
          await page
            .locator(
              `[data-download="hero"] .package-options [data-arch="${arch}"]`,
            )
            .click();
          await checkDownloads(page, release);
        }
        const formats = await page
          .locator('[data-download="hero"] [data-package-format]')
          .evaluateAll((es) => es.map((e) => e.dataset.packageFormat));
        for (const format of formats) {
          await page
            .locator(`[data-download="hero"] [data-package-format="${format}"]`)
            .click();
          await checkDownloads(page, release);
          const href = await ctas(page).first().getAttribute("href");
          assert.ok(
            release.packages.some(
              (p) =>
                p.os === os &&
                p.file === format &&
                new URL(p.url, origin).href === new URL(href, origin).href,
            ),
            "format selector must select matching package",
          );
        }
      }
      if (width <= 768) {
        const menu = page.locator(".menu-toggle");
        await menu.click();
        assert.equal(await page.locator("#mobile-nav").isVisible(), true);
        await page.keyboard.press("Escape");
        assert.equal(await page.locator("#mobile-nav").isVisible(), false);
        assert.equal(await menu.getAttribute("aria-expanded"), "false");
        await menu.click();
        await page.locator("#mobile-nav a").first().click();
        assert.equal(await page.locator("#mobile-nav").isVisible(), false);
      }
      await page.evaluate(() => scrollTo(0, 0));
      await screenshot(page, `${lang}-${width}-hero`);
      const sections = page.locator("main > section");
      assert.ok((await sections.count()) >= 7, "landing sections missing");
      for (let i = 1; i < (await sections.count()); i++) {
        const section = sections.nth(i);
        const id = await section.getAttribute("id");
        assert.ok(id, "section missing id");
        await section.evaluate((el) => el.scrollIntoView({ block: "start" }));
        await screenshot(page, `${lang}-${width}-${id}`);
      }
      report.layouts.push(`${lang}/${width}`);
    }
    const release = await page.evaluate(() => window.OMR.getRelease());
    if (release.packages.length) {
      const pkg = release.packages[0];
      await page
        .locator(`[data-download="hero"] [data-os="${pkg.os}"]`)
        .click();
      const arch = page.locator(
        `[data-download="hero"] .package-options [data-arch="${pkg.arch}"]`,
      );
      if (await arch.count()) await arch.click();
      const format = page.locator(
        `[data-download="hero"] [data-package-format="${pkg.format}"]`,
      );
      if (await format.count()) await format.click();
      await checkDownloads(page, release);
      assert.equal(await page.locator(".checksum").textContent(), pkg.sha256);
      await page.locator("#checksum-details > summary").click();
      await page.evaluate(() =>
        Object.defineProperty(navigator, "clipboard", {
          configurable: true,
          value: {
            writeText: async (text) => {
              window.__copied = text;
            },
          },
        }),
      );
      await page.locator("[data-copy-checksum]").click();
      assert.equal(await page.evaluate(() => window.__copied), pkg.sha256);
      assert.equal(await page.locator(".toast").isVisible(), true);
      const success = await page.locator(".toast").innerText();
      assert.ok(success.trim());
      await page.evaluate(() =>
        Object.defineProperty(navigator, "clipboard", {
          configurable: true,
          value: {
            writeText: async () => {
              throw Error("denied");
            },
          },
        }),
      );
      await page.locator("[data-copy-checksum]").click();
      assert.equal(await page.locator(".toast").isVisible(), true);
      const failure = await page.locator(".toast").innerText();
      assert.ok(failure.trim());
      assert.notEqual(failure, success);
      assert.equal(
        await page.evaluate(() => String(window.getSelection())),
        pkg.sha256,
      );
    } else
      report.skipped.push(`${lang}: clipboard requires a published package`);
    for (const width of [390, 1280]) {
      await page.setViewportSize({ width, height: 900 });
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      report.axe.push({ lang, width, violations: results.violations });
      assert.deepEqual(results.violations, [], `axe ${lang}/${width}`);
    }
    await context.close();
    const nojs = await browser.newContext({ javaScriptEnabled: false });
    const staticPage = await nojs.newPage();
    watch(staticPage);
    await staticPage.goto(url(lang), { waitUntil: "networkidle" });
    const manifest = await staticPage
      .locator("#release-data")
      .evaluate((el) => JSON.parse(el.textContent));
    assert.equal(await staticPage.locator(".all-packages").count(), 1);
    await staticPage.locator(".all-packages > summary").click();
    const links = await staticPage
      .locator(".all-packages a[href]")
      .evaluateAll((es) => es.map((e) => e.href));
    for (const pkg of manifest.packages) {
      assert.ok(
        links.includes(new URL(pkg.url, origin).href),
        `static download missing ${pkg.file}`,
      );
      assert.ok(
        links.includes(new URL(pkg.checksumUrl, origin).href),
        `static checksum missing ${pkg.file}`,
      );
    }
    await nojs.close();
  }
  const cases = [
    [
      { platform: "MacIntel", userAgent: "Macintosh Intel Mac OS X" },
      { os: "macos", arch: null, mobile: false },
    ],
    [
      { platform: "MacIntel", userAgent: "Macintosh", maxTouchPoints: 5 },
      { os: null, arch: null, mobile: true },
    ],
    [
      { platform: "Win32", userAgent: "Windows NT ARM64" },
      { os: "windows", arch: "arm64", mobile: false },
    ],
    [
      {
        platform: "Win32",
        userAgent: "Windows NT",
        architecture: "x86",
        bitness: "32",
      },
      { os: "windows", arch: "x86", mobile: false },
    ],
    [
      { platform: "Linux aarch64", userAgent: "Linux aarch64" },
      { os: "linux", arch: "arm64", mobile: false },
    ],
    [
      { platform: "", userAgent: "unknown" },
      { os: null, arch: null, mobile: false },
    ],
    [
      {
        platform: "MacIntel",
        userAgent: "Macintosh",
        architecture: "arm",
        bitness: "64",
      },
      { os: "macos", arch: "arm64", mobile: false },
    ],
  ];
  const context = await browser.newContext();
  const page = await context.newPage();
  watch(page);
  await page.goto(url("en"), { waitUntil: "networkidle" });
  for (const [input, expected] of cases) {
    const actual = await page.evaluate(
      (input) => window.OMR.detectPlatform(input),
      input,
    );
    assert.deepEqual(actual, expected);
    report.detection.push({ input, actual });
  }
  await context.close();
  // Synthetic release matrices exercise controls only; no fixture file is downloaded.
  const syntheticControls = [];
  for (const matrix of [
    {
      os: "linux",
      platform: "Linux aarch64",
      ua: "Linux aarch64",
      format: "AppImage",
    },
    { os: "windows", platform: "Win32", ua: "Windows NT ARM64", format: "msi" },
    { os: "macos", platform: "MacIntel", ua: "Macintosh", format: null },
    { os: "macos", platform: "MacIntel", ua: "Macintosh", format: "dmg" },
    {
      os: "macos",
      platform: "MacIntel",
      ua: "Macintosh",
      format: "dmg",
      mixed: true,
      lang: "en",
    },
    {
      os: "macos",
      platform: "MacIntel",
      ua: "Macintosh",
      format: "dmg",
      mixed: true,
      lang: "fr",
    },
  ]) {
    const fixtureContext = await browser.newContext();
    await fixtureContext.addInitScript(({ platform, ua }) => {
      Object.defineProperty(navigator, "platform", { value: platform });
      Object.defineProperty(navigator, "userAgent", { value: ua });
      Object.defineProperty(navigator, "maxTouchPoints", { value: 0 });
      Object.defineProperty(navigator, "userAgentData", { value: undefined });
    }, matrix);
    const fixture = await fixtureContext.newPage();
    watch(fixture);
    const packages = matrix.format
      ? [
          {
            version: "0.1.0",
            sourceCommit: "a".repeat(40),
            os: matrix.os,
            arch: "x64",
            format: matrix.format,
            bytes: 1024,
            file: `synthetic-control.${matrix.format}`,
            sha256: "a".repeat(64),
            url: `/synthetic-controls/package.${matrix.format}`,
            checksumUrl: `/synthetic-controls/package.${matrix.format}.sha256`,
          },
        ]
      : [];
    if (matrix.mixed) {
      packages.push({
        ...packages[0],
        version: "0.3.0",
        sourceCommit: "b".repeat(40),
        arch: "arm64",
        file: "synthetic-control-arm64.dmg",
        url: "/synthetic-controls/package-arm64.dmg",
        checksumUrl: "/synthetic-controls/package-arm64.dmg.sha256",
      });
      packages.push({
        ...packages[0],
        arch: "arm64",
        file: "synthetic-control-arm64-old.dmg",
        url: "/synthetic-controls/package-arm64-old.dmg",
        checksumUrl: "/synthetic-controls/package-arm64-old.dmg.sha256",
      });
    }
    const locale = matrix.lang || "en";
    await fixture.route(`**/${locale}/`, async (route) => {
      const response = await route.fetch();
      const html = (await response.text()).replace(
        /(<script id="release-data" type="application\/json">)[\s\S]*?(<\/script>)/,
        (_, start, end) =>
          start +
          JSON.stringify({
            packages,
          }) +
          end,
      );
      await route.fulfill({ response, body: html });
    });
    await fixture.goto(url(locale), { waitUntil: "networkidle" });
    const panel = fixture.locator('[data-download="hero"]');
    if (!matrix.format) {
      assert.equal(
        await fixture.locator("[data-arch]:not(:disabled)").count(),
        0,
        "no live architecture control when no macOS package exists",
      );
      assert.equal(await fixture.locator(".download-cta[href]").count(), 0);
    } else {
      if (matrix.os === "macos") {
        if (!matrix.mixed)
          assert.equal(
            await fixture.locator('[data-arch="arm64"]:not(:disabled)').count(),
            0,
            "missing Apple Silicon package cannot leave an inert enabled control",
          );
      } else {
        const label = await panel.locator('[data-arch="x64"]').innerText();
        assert.ok(
          label.includes(`.${matrix.format}`),
          `fallback must show actual ${matrix.format}, received ${label}`,
        );
      }
      const option = panel.locator('[data-arch="x64"]');
      await option.click();
      await checkDownloads(fixture, { packages });
      assert.equal(
        await panel.locator(".download-cta").getAttribute("href"),
        packages[0].url,
      );
      await panel.locator('[data-arch="x64"]').press("Home");
      assert.equal(
        await fixture.evaluate(() => document.activeElement.dataset.arch),
        matrix.mixed ? "arm64" : "x64",
        "keyboard skips unavailable architectures",
      );
      if (matrix.mixed) {
        for (const width of [320, 390, 1280]) {
          await fixture.setViewportSize({ width, height: 900 });
          for (const arch of ["arm64", "x64"]) {
            await panel.locator(`[data-arch="${arch}"]`).click();
            await checkDownloads(fixture, { packages });
            if (arch === "arm64") {
              const formats = panel.locator("[data-package-format]");
              const labels = await formats.allTextContents();
              assert.equal(
                new Set(labels).size,
                2,
                "Retained and new versions must have distinct labels",
              );
              for (const pkg of packages.filter((p) => p.arch === arch)) {
                const option = panel.locator(
                  `[data-package-format="${pkg.file}"]`,
                );
                assert.ok(
                  (await option.textContent()).includes(`v${pkg.version}`),
                );
                await option.click();
                await checkDownloads(fixture, { packages });
              }
            }
            assert.equal(
              await fixture.evaluate(
                () => document.documentElement.scrollWidth <= innerWidth,
              ),
              true,
            );
          }
        }
        await panel.locator('[data-arch="arm64"]').click();
        await panel
          .locator('[data-package-format="synthetic-control-arm64.dmg"]')
          .click();
        await checkDownloads(fixture, { packages });
        await screenshot(fixture, `synthetic-mixed-versions-${locale}`);
      }
    }
    syntheticControls.push(matrix);
    await fixtureContext.close();
  }
  report.syntheticControls = syntheticControls;
  assert.deepEqual(
    report.errors,
    [],
    "browser errors or unexpected network requests",
  );
  await writeFile(
    join(output, "report.json"),
    JSON.stringify(report, null, 2) + "\n",
  );
  console.log(
    JSON.stringify({
      result: "PASS",
      layouts: report.layouts.length,
      scenarios: report.scenarios.length,
      detection: report.detection.length,
      screenshots: report.screenshots.length,
      skipped: report.skipped,
    }),
  );
} catch (error) {
  await writeFile(
    join(output, "failure.json"),
    JSON.stringify({ ...report, failure: error.stack }, null, 2) + "\n",
  );
  throw error;
} finally {
  await browser?.close();
  if (server) await new Promise((r) => server.close(r));
}
