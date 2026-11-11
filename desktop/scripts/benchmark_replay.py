"""Production frontend interaction replay with synthetic benchmark/native data."""

import asyncio
import copy
import json
import sys
import tempfile
import threading
import time
import uuid
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from playwright.async_api import async_playwright, expect
from desktop_engine import Runtime
from desktop_benchmarks import parse
from test_desktop_benchmarks import fixture


async def main(evidence):
    evidence.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="benchmark-ui-") as home:
        runtime = Runtime(home, "synthetic-gateway-key-" * 4)
        config = runtime.snapshot()["config"]
        connection = str(uuid.uuid4())
        config["connections"] = [
            {
                "id": connection,
                "name": "Synthetic Benchmark Fixture",
                "url": "http://127.0.0.1:1/v1",
                "models": [],
            }
        ]
        runtime.save_config(config, 0)
        calls, errors = [], []
        dataset = fixture()
        delay = 0

        async def native(_source, name, args):
            if name == "engine":
                request = args["request"]
                action = request["command"]
                if action == "snapshot":
                    return runtime.snapshot()
                if action == "save_config":
                    return runtime.save_config(
                        request["config"],
                        request["revision"],
                        request.get("consent_for"),
                    )
                if action == "discover":
                    return ["small", "middle", "large", "unmatched:quant"]
                if action == "benchmark_refresh":
                    calls.append(copy.deepcopy(request))
                    await asyncio.sleep(delay)
                    result = {
                        **parse(dataset),
                        "configured": True,
                        "error": None,
                        "fetched_at": time.time(),
                        "retry_at": 0,
                    }
                    runtime.benchmark_data = result
                    return result
                raise RuntimeError("unexpected_fixture_command")
            if name == "plugin:autostart|is_enabled":
                return False
            if name == "plugin:event|listen":
                return 1
            if name == "plugin:event|unlisten":
                return None
            raise RuntimeError("unexpected_fixture_invoke")

        class Assets(SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(Assets, directory=str(ROOT / "desktop/dist"))
        )
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    executable_path="/usr/bin/brave-browser",
                    headless=True,
                    chromium_sandbox=True,
                )
                try:
                    page = await browser.new_page(
                        viewport={"width": 1280, "height": 1000}
                    )
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    await page.expose_binding("nativeReplay", native)
                    await page.add_init_script("""
                        localStorage.setItem('omr:onboarding:v1', JSON.stringify({open:false,step:0}));
                        window.snapshotReads = 0;
                        window.__TAURI_INTERNALS__ = {invoke: (command,args) => {
                            if (args?.request?.command === 'snapshot') window.snapshotReads++;
                            return window.nativeReplay(command,args);
                        }, transformCallback: () => 1, unregisterCallback: () => {}};
                        window.__TAURI_EVENT_PLUGIN_INTERNALS__ = {unregisterListener: () => {}};
                    """)
                    await page.goto(f"http://127.0.0.1:{server.server_port}")
                    nav = page.get_by_role("navigation", name="Navigation principale")
                    advanced = nav.locator("details")
                    await expect(nav.get_by_role("button", name="Inspecteur", exact=True)).to_be_hidden()
                    await advanced.locator("summary").press("Enter")
                    await expect(nav.get_by_role("button", name="Inspecteur", exact=True)).to_be_visible()
                    await page.wait_for_function("window.snapshotReads > 1", timeout=10000)
                    await expect(advanced).to_have_attribute("open", "")
                    await nav.get_by_role("button", name="Profils & règles", exact=True).click()
                    await expect(page.get_by_role("heading", name="Profils & règles", exact=True)).to_be_visible()
                    await expect(advanced).to_have_attribute("open", "")
                    await nav.get_by_role("button", name="Chat", exact=True).click()
                    await expect(page.get_by_role("heading", name="Chat", exact=True)).to_be_visible()
                    await expect(nav.get_by_role("button", name="Inspecteur", exact=True)).to_be_hidden()
                    await page.screenshot(path=str(evidence / "everyday-chat.png"), full_page=True)
                    await page.get_by_role("button", name="État", exact=True).click()
                    await page.get_by_role("button", name="Tout voir", exact=True).click()
                    await expect(page.get_by_role("heading", name="Inspecteur", exact=True)).to_be_visible()
                    await expect(advanced).to_have_attribute("open", "")
                    await page.get_by_role(
                        "button", name="Fournisseurs", exact=True
                    ).click()
                    ranking = page.get_by_role("region", name="Classement des modèles")
                    await expect(ranking).to_be_visible()
                    await expect(
                        ranking.get_by_text("Données récupérées le", exact=False)
                    ).to_be_visible()
                    await page.get_by_role(
                        "button", name="Découvrir les modèles", exact=True
                    ).click()
                    before = len(calls)
                    for name in ["small", "middle", "large", "unmatched:quant"]:
                        await page.get_by_role(
                            "checkbox", name=name, exact=True
                        ).click()
                    await asyncio.sleep(1.6)
                    assert len(calls) - before == 1, calls
                    saved = runtime.config["connections"][0]["models"]
                    assert {m["upstream"]: m["quality"] for m in saved} == {
                        "small": 1,
                        "middle": 2,
                        "large": 3,
                        "unmatched:quant": 0,
                    }
                    assert all(m["enabled"] for m in saved)
                    await expect(
                        ranking.get_by_text("Non classé par le benchmark", exact=True)
                    ).to_have_count(1)
                    await page.screenshot(
                        path=str(evidence / "ranking-initial.png"), full_page=True
                    )

                    # A late source response must preserve a newer manual correction.
                    delay = 0.6
                    dataset["data"][1]["evaluations"][
                        "artificial_analysis_intelligence_index"
                    ] = 80
                    await ranking.get_by_role(
                        "button", name="Actualiser le classement", exact=True
                    ).click()
                    await ranking.get_by_role(
                        "combobox", name="Niveau de large", exact=True
                    ).click()
                    await page.get_by_role(
                        "option", name="1 · manuel", exact=True
                    ).click()
                    await asyncio.sleep(1.3)
                    model = next(
                        m
                        for m in runtime.config["connections"][0]["models"]
                        if m["upstream"] == "large"
                    )
                    assert (
                        model["quality"] == 1 and model["quality_mode"] == "manual"
                    ), model
                    await ranking.get_by_role(
                        "combobox", name="Niveau de large", exact=True
                    ).click()
                    await page.get_by_role(
                        "option", name="Automatique · 2", exact=True
                    ).click()
                    await asyncio.sleep(0.6)
                    model = next(
                        m
                        for m in runtime.config["connections"][0]["models"]
                        if m["upstream"] == "large"
                    )
                    assert (
                        model["quality"] == 2 and model["quality_mode"] == "benchmark"
                    ), model

                    # Explicit association, not fuzzy matching, enables a private alias.
                    await ranking.get_by_label(
                        "Référence benchmark de unmatched:quant", exact=True
                    ).fill("large")
                    await asyncio.sleep(0.6)
                    model = next(
                        m
                        for m in runtime.config["connections"][0]["models"]
                        if m["upstream"] == "unmatched:quant"
                    )
                    assert (
                        model["quality"] == 2 and model["benchmark_model"] == "large"
                    ), model
                    before = len(calls)
                    delay = 1.2
                    await ranking.get_by_role(
                        "button", name="Actualiser le classement", exact=True
                    ).click()
                    await page.get_by_role("checkbox", name="small", exact=True).click()
                    await asyncio.sleep(2.9)
                    assert len(calls) - before == 2, calls
                    assert "small" not in [
                        m["upstream"]
                        for m in runtime.config["connections"][0]["models"]
                    ]
                    await page.screenshot(
                        path=str(evidence / "ranking-manual-and-reference.png"),
                        full_page=True,
                    )
                    await page.get_by_role("button", name="État", exact=True).click()
                    await expect(ranking).to_be_hidden()
                    assert not errors, errors
                    report = {
                        "status": "pass",
                        "source": "synthetic",
                        "native_boundary": "substituted",
                        "checks": [
                            "everyday navigation hides advanced pages",
                            "native keyboard disclosure",
                            "engine polling preserves user disclosure",
                            "advanced navigation and shortcut reveal selection",
                            "return to Chat closes advanced disclosure",
                            "visible source/score/levels",
                            "debounced bulk selection",
                            "automatic source tiers",
                            "unmatched stays unranked",
                            "late response preserves manual override",
                            "restore benchmark mode",
                            "explicit source association",
                            "debounced removal",
                            "hidden away from providers",
                            "no JavaScript errors",
                        ],
                        "refresh_calls": len(calls),
                        "configuration_revision": runtime.revision,
                    }
                    (evidence / "report.json").write_text(json.dumps(report, indent=2))
                    print(json.dumps(report))
                finally:
                    await browser.close()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1])))
