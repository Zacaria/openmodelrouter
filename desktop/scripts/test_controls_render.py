"""Synthetic hydrated shared controls in Brave/Linux; not a native macOS replay."""

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--css", type=Path)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    css_paths = [args.css] if args.css else sorted((ROOT / "dist/assets").glob("*.css"))
    if not css_paths:
        raise SystemExit("Build the frontend first or specify --css")
    css = "\n".join(p.read_text() for p in css_paths)
    subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            """import {build} from 'vite'; import react from '@vitejs/plugin-react';
await build({configFile:false, plugins:[react()], define:{'process.env.NODE_ENV':'"production"'}, build:{
lib:{entry:'src/components/controls.fixture.tsx', name:'OMRControlsFixture',
formats:['iife'],fileName:()=> 'fixture.js'},
outDir:'test-results/controls-runtime',emptyOutDir:true,minify:true}});""",
        ],
        cwd=ROOT,
        check=True,
    )
    fixture = (ROOT / "test-results/controls-runtime/fixture.js").read_text()
    args.evidence.mkdir(parents=True, exist_ok=True)
    checks = []

    def check(name, actual, expected: object = True):
        checks.append(
            {
                "name": name,
                "actual": actual,
                "expected": expected,
                "pass": actual == expected,
            }
        )

    with sync_playwright() as p:
        executable = shutil.which("brave-browser")
        if not executable:
            raise SystemExit("Brave is required for this Linux replay")
        browser = p.chromium.launch(
            executable_path=executable, headless=True, args=["--disable-gpu"]
        )
        browser_version = browser.version
        context = browser.new_context()
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def value(name):
            return page.locator(f'input[type=hidden][name="{name}"]').input_value()

        def token_color(token):
            return page.evaluate(
                """token => { const e = document.createElement('span');
                e.style.backgroundColor = `var(${token})`; document.body.append(e);
                const color = getComputedStyle(e).backgroundColor; e.remove(); return color; }""",
                token,
            )

        for theme in ("light", "dark"):
            for width in (800, 1180):
                page.set_viewport_size({"width": width, "height": 1100})
                page.set_content(
                    f'<!doctype html><html lang="fr" data-theme="{theme}"><head><style>{css}</style></head><body><div id="root"></div></body></html>'
                )
                page.add_script_tag(content=fixture)
                transport = page.get_by_role(
                    "combobox", name="Transport fournisseur", exact=True
                )
                transport.wait_for()
                prefix = f"{theme}/{width}"
                styles = page.locator(
                    "button:visible, input:visible, textarea"
                ).evaluate_all("""els => els.map(e => {
                    const s = getComputedStyle(e); return {tag: e.tagName, type: e.type, appearance: s.appearance,
                    font: s.fontFamily, color: s.color, background: s.backgroundColor}; })""")
                for index, style in enumerate(styles):
                    check(
                        f"{prefix}/{index}/{style['tag']}: no system skin",
                        style["appearance"],
                        "none",
                    )
                check(
                    f"{prefix}: textarea inherits interface font",
                    page.locator("textarea").evaluate(
                        "e => getComputedStyle(e).fontFamily === getComputedStyle(document.body).fontFamily"
                    ),
                )
                check(
                    f"{prefix}: select has explicit indicator",
                    transport.locator(".select-chevron").is_visible(),
                )
                page.get_by_label("Nom", exact=True).fill("Connexion synthétique")
                page.get_by_label("Nom", exact=True).press("Tab")
                check(
                    f"{prefix}: Tab reaches labelled select",
                    transport.evaluate("e => e === document.activeElement"),
                )
                check(
                    f"{prefix}: keyboard focus visible",
                    transport.evaluate(
                        "e => getComputedStyle(e).outlineStyle !== 'none'"
                    ),
                )
                page.screenshot(
                    path=str(args.evidence / f"linux-brave-{theme}-{width}.png"),
                    full_page=True,
                )
                transport.press("Space")
                menu = page.get_by_role("listbox")
                menu.wait_for()
                expect(menu.locator("[data-highlighted]")).to_contain_text("HTTP")
                check(f"{prefix}: open menu is styleable OMR listbox", menu.count(), 1)
                check(
                    f"{prefix}: popup uses panel token",
                    menu.evaluate("e => getComputedStyle(e).backgroundColor"),
                    token_color("--panel"),
                )
                check(
                    f"{prefix}: selected choice marked",
                    menu.locator('[data-state="checked"]').inner_text(),
                    "✓\nHTTP",
                )
                page.keyboard.press("ArrowDown")
                highlighted = menu.locator("[data-highlighted]")
                expect(highlighted).to_have_text("pi-ai")
                check(
                    f"{prefix}: arrow highlights next choice",
                    highlighted.inner_text(),
                    "pi-ai",
                )
                check(
                    f"{prefix}: highlight uses OMR background",
                    highlighted.evaluate("e => getComputedStyle(e).backgroundColor"),
                    token_color("--selected-bg"),
                )
                check(
                    f"{prefix}: highlight uses OMR text",
                    highlighted.evaluate("e => getComputedStyle(e).color"),
                    token_color("--selected"),
                )
                check(
                    f"{prefix}: navigation is uncommitted", value("transport"), "http"
                )
                page.screenshot(
                    path=str(
                        args.evidence / f"linux-brave-{theme}-{width}-select-open.png"
                    ),
                    full_page=True,
                )
                page.keyboard.press("ArrowDown")
                expect(menu.locator("[data-highlighted]")).to_have_text("Local")
                check(
                    f"{prefix}: disabled choice skipped",
                    menu.locator("[data-highlighted]").inner_text(),
                    "Local",
                )
                page.keyboard.press("Escape")
                check(
                    f"{prefix}: Escape keeps current selection",
                    value("transport"),
                    "http",
                )
                check(
                    f"{prefix}: Escape returns focus",
                    transport.evaluate("e => e === document.activeElement"),
                )
                transport.press("Space")
                menu.wait_for()
                expect(menu.locator("[data-highlighted]")).to_contain_text("HTTP")
                page.keyboard.press("p")
                expect(menu.locator("[data-highlighted]")).to_have_text("pi-ai")
                check(
                    f"{prefix}: typeahead reaches pi-ai",
                    menu.locator("[data-highlighted]").inner_text(),
                    "pi-ai",
                )
                page.keyboard.press("Enter")
                menu.wait_for(state="hidden")
                check(
                    f"{prefix}: Enter commits application value",
                    value("transport"),
                    "pi-ai",
                )
                check(
                    f"{prefix}: trigger displays committed choice",
                    transport.inner_text(),
                    "pi-ai\n▾",
                )
                check(
                    f"{prefix}: trigger does not submit form",
                    page.get_by_test_id("submit-count").inner_text(),
                    "0",
                )
                check(
                    f"{prefix}: form gets original value only",
                    page.locator("form").evaluate(
                        "e => new FormData(e).getAll('transport')"
                    ),
                    ["pi-ai"],
                )
                check(
                    f"{prefix}: disabled field absent from form",
                    page.locator("form").evaluate(
                        "e => new FormData(e).has('disabled-choice')"
                    ),
                    False,
                )
                check(
                    f"{prefix}: select disabled",
                    page.get_by_role(
                        "combobox", name="Sélecteur indisponible"
                    ).is_disabled(),
                )
                baseline = page.get_by_role("combobox", name="Modèle de référence")
                check(
                    f"{prefix}: empty choice displayed",
                    baseline.inner_text(),
                    "Aucune référence\n▾",
                )
                baseline.click()
                menu.wait_for()
                page.get_by_role(
                    "option", name="Valeur ressemblant à une sentinelle"
                ).click()
                check(
                    f"{prefix}: sentinel-like value preserved",
                    value("baseline"),
                    "value:",
                )
                baseline.click()
                menu.wait_for()
                page.keyboard.press("End")
                expect(menu.locator("[data-highlighted]")).to_contain_text(
                    "synthétique 39"
                )
                check(
                    f"{prefix}: long list keyboard reaches last",
                    "synthétique 39" in menu.locator("[data-highlighted]").inner_text(),
                )
                check(
                    f"{prefix}: long list stays within viewport",
                    menu.evaluate(
                        "e => { const r=e.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight; }"
                    ),
                )
                page.screenshot(
                    path=str(
                        args.evidence / f"linux-brave-{theme}-{width}-long-menu.png"
                    ),
                    full_page=True,
                )
                page.keyboard.press("Home")
                expect(menu.locator("[data-highlighted]")).to_contain_text(
                    "Aucune référence"
                )
                viewport = menu.locator(".select-viewport")
                viewport.hover()
                page.mouse.wheel(0, 300)
                page.wait_for_function(
                    "document.querySelector('.select-viewport').scrollTop > 0"
                )
                check(
                    f"{prefix}: long list scrolls with mouse wheel",
                    viewport.evaluate("e => e.scrollTop > 0"),
                )
                page.keyboard.press("End")
                expect(menu.locator("[data-highlighted]")).to_contain_text(
                    "synthétique 39"
                )
                page.keyboard.press("Home")
                expect(menu.locator("[data-highlighted]")).to_contain_text(
                    "Aucune référence"
                )
                page.keyboard.press("Enter")
                check(f"{prefix}: empty value round-trips", value("baseline"), "")
                check(
                    f"{prefix}: wrapping filter label names trigger",
                    page.get_by_role("combobox", name="Période").count(),
                    1,
                )
                page.locator("label").filter(has_text="Chat JSON").click()
                check(
                    f"{prefix}: label toggles checkbox",
                    page.locator("[name=protocol]").is_checked(),
                )
                check(
                    f"{prefix}: checked marker visible",
                    page.locator("[name=protocol]").evaluate(
                        "e => getComputedStyle(e, '::before').visibility"
                    ),
                    "visible",
                )
                page.locator("[name=protocol]").press("Space")
                check(
                    f"{prefix}: Space toggles checkbox",
                    page.locator("[name=protocol]").is_checked(),
                    False,
                )
                page.get_by_label("Qualité déclarée").press("ArrowUp")
                check(
                    f"{prefix}: number keyboard step retained",
                    page.get_by_label("Qualité déclarée").input_value(),
                    "3",
                )
                check(
                    f"{prefix}: readonly retained",
                    page.get_by_label("Chemin").get_attribute("readonly") is not None,
                )
                check(
                    f"{prefix}: disabled retained",
                    page.get_by_role(
                        "textbox", name="Indisponible", exact=True
                    ).is_disabled(),
                )
                page.get_by_role("button", name="Ouvrir le dialogue").click()
                dialog = page.get_by_role("dialog")
                dialog.wait_for()
                dialog.get_by_role("combobox").click()
                menu.wait_for()
                check(
                    f"{prefix}: portalled menu in dialog uses OMR",
                    menu.evaluate("e => getComputedStyle(e).backgroundColor"),
                    token_color("--panel"),
                )
                page.screenshot(
                    path=str(
                        args.evidence / f"linux-brave-{theme}-{width}-dialog-menu.png"
                    ),
                    full_page=True,
                )
                page.get_by_role("option", name="HTTP", exact=True).click()
                check(f"{prefix}: dialog menu commits", value("transport"), "http")
                check(
                    f"{prefix}: choosing option keeps dialog open", dialog.is_visible()
                )
                page.keyboard.press("Escape")
                dialog.wait_for(state="hidden")
                check(
                    f"{prefix}: no overflow",
                    page.evaluate("document.documentElement.scrollWidth <= innerWidth"),
                )
                (args.evidence / f"linux-brave-{theme}-{width}-styles.json").write_text(
                    json.dumps(styles, indent=2)
                )
        page.emulate_media(forced_colors="active")
        check(
            "forced colors: native checkbox restored",
            page.locator("[name=protocol]").evaluate(
                "e => getComputedStyle(e).appearance"
            ),
            "auto",
        )
        check(
            "forced colors: custom checkbox marker removed",
            page.locator("[name=protocol]").evaluate(
                "e => getComputedStyle(e, '::before').display"
            ),
            "none",
        )
        transport.click()
        menu.wait_for()
        expect(menu.locator("[data-highlighted]")).to_be_visible()
        check("forced colors: custom menu remains operable", menu.is_visible())
        check(
            "forced colors: highlighted choice preserves system contrast",
            menu.locator("[data-highlighted]").evaluate(
                "e => getComputedStyle(e).forcedColorAdjust"
            ),
            "none",
        )
        page.screenshot(
            path=str(args.evidence / "linux-brave-forced-colors.png"), full_page=True
        )
        page.keyboard.press("Escape")
        check("no browser runtime errors", errors, [])
        context.close()
        browser.close()
    report = {
        "environment": "Linux / isolated Brave / hydrated React shared-component fixture",
        "os": platform.platform(),
        "browser_version": browser_version,
        "css_sha256": hashlib.sha256(css.encode()).hexdigest(),
        "fixture_sha256": hashlib.sha256(fixture.encode()).hexdigest(),
        "checks": checks,
    }
    (args.evidence / "report.json").write_text(json.dumps(report, indent=2))
    failed = [c for c in checks if not c["pass"]]
    for c in failed:
        print(f"FAIL {c['name']}: {c['actual']!r} != {c['expected']!r}")
    print(
        f"{len(checks) - len(failed)}/{len(checks)} checks passed; {len(failed)} failures"
    )
    raise SystemExit(bool(failed))


if __name__ == "__main__":
    main()
