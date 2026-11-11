import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";

const source = readFileSync(
  new URL("../src/language-routing.js", import.meta.url),
  "utf8",
);

function run({
  path = "/",
  hash = "",
  languages = [],
  language = "",
  stored = null,
  blocked = false,
} = {}) {
  const links = ["en", "fr"].map((lang) => ({
    dataset: { language: lang },
    href: `/${lang}/`,
    addEventListener(_event, callback) {
      this.click = callback;
    },
  }));
  let replacement;
  const storage = {
    getItem() {
      if (blocked) throw Error("unavailable");
      return stored;
    },
    setItem(_key, value) {
      if (blocked) throw Error("unavailable");
      stored = value;
    },
  };
  runInNewContext(source, {
    navigator: { languages, language },
    localStorage: storage,
    location: {
      pathname: path,
      hash,
      replace(value) {
        replacement = value;
      },
    },
    document: {
      querySelectorAll() {
        return links;
      },
    },
  });
  return {
    links,
    replacement,
    get stored() {
      return stored;
    },
  };
}

test("root respects a saved manual preference before browser languages", () => {
  assert.equal(
    run({ stored: "fr", languages: ["en-US"], hash: "#faq" }).replacement,
    "/fr/#faq",
  );
});

test("root selects first supported regional browser language and falls back to English", () => {
  assert.equal(
    run({ languages: ["de-DE", "FR-ca", "en-US"] }).replacement,
    "/fr/",
  );
  assert.equal(run({ language: "fr-CA" }).replacement, "/fr/");
  assert.equal(
    run({ languages: ["de", "ja"], language: "fr" }).replacement,
    "/en/",
  );
  assert.equal(
    run({ stored: "bogus", blocked: true, languages: ["fr"] }).replacement,
    "/fr/",
  );
});

test("explicit language is not redirected and manual selection preserves section and persists", () => {
  const result = run({ path: "/en/", hash: "#faq", stored: "fr" });
  assert.equal(result.replacement, undefined);
  assert.equal(result.links[1].href, "/fr/#faq");
  result.links[1].click();
  assert.equal(result.stored, "fr");
});

test("unavailable storage does not stop language links", () => {
  const result = run({ path: "/fr/", hash: "#profils", blocked: true });
  assert.equal(result.links[0].href, "/en/#profils");
  assert.doesNotThrow(() => result.links[0].click());
});

test("both prerendered locales contain translated content and the same section targets", () => {
  const en = readFileSync(
    new URL("../dist/en/index.html", import.meta.url),
    "utf8",
  );
  const fr = readFileSync(
    new URL("../dist/fr/index.html", import.meta.url),
    "utf8",
  );
  assert.match(en, /<html lang="en">/);
  assert.match(fr, /<html lang="fr">/);
  assert.ok(en.includes("Every request."));
  assert.ok(fr.includes("Chaque requête."));
  for (const html of [en, fr]) {
    for (const id of [
      "pourquoi",
      "profils",
      "capacites",
      "fonctionnement",
      "faq",
      "disponibilite",
      "integration",
      "scenario-data",
      "release-data",
    ])
      assert.ok(html.includes(`id="${id}"`), id);
    for (const lang of ["en", "fr"])
      assert.ok(html.includes(`data-language="${lang}"`));
    assert.ok(html.includes('src="/language-routing.js"'));
    assert.doesNotMatch(
      html,
      /type="checkbox"|Suspendre le flux|non signé|paquet non signé/i,
    );
  }
});
