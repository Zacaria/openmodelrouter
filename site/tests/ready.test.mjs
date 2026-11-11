import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
test("GitHub remains explicitly unavailable without a visitor link", () => {
  for (const lang of ["en", "fr"]) {
    const html = readFileSync(`src/templates/${lang}.html`, "utf8");
    assert.match(
      html,
      /<span\s+class="github-unavailable"\s*>[\s\S]*?GitHub[\s\S]*?<\/span\s*>/,
    );
    assert.doesNotMatch(
      html,
      /<a\b[^>]*href="https?:\/\/(?:www\.)?github\.com\//i,
    );
  }
});
test("both languages link the public macOS ARM64 0.3.0 source materials", () => {
  for (const lang of ["en", "fr"]) {
    const html = readFileSync(`dist/${lang}/index.html`, "utf8");
    assert.ok(
      /href="https:\/\/open-model-router-materials-3\.vercel\.app\/"/.test(
        html,
      ),
      "Missing public source materials link",
    );
    assert.ok(/(?:Sources|sources).*0\.3\.0.*ARM64/s.test(html));
  }
});
test("built landing retains supplied interactive scenario explorer", () => {
  const html = readFileSync("dist/en/index.html", "utf8");
  assert.match(html, /class="scenario-explorer"/);
  assert.match(html, /data-scenario="vision"/);
});
