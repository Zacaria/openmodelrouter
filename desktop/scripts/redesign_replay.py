"""Replay the built redesign in isolated Brave with synthetic native IPC.

Run after npm run build:
uv run --with playwright python desktop/scripts/redesign_replay.py EVIDENCE_DIR
This checks presentation, not a packaged native application or real credentials.
"""

import asyncio
import json
import sys
import tempfile
import threading
import uuid
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from desktop_engine import Runtime
from playwright.async_api import async_playwright, expect


async def main(evidence):
    evidence.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="omr-redesign-") as home:
        runtime = Runtime(home, "synthetic-redesign-gateway-" * 4)
        runtime.port = 12001
        calls, errors, requests = [], [], []
        fail_snapshot = False

        async def native(_source, name, args=None):
            calls.append(name)
            if name == "engine":
                assert args is not None
                request = args["request"]
                action = request["command"]
                if action == "snapshot":
                    if fail_snapshot:
                        raise RuntimeError("engine_disconnected")
                    return runtime.snapshot()
                if action == "save_config":
                    return runtime.save_config(request["config"], request["revision"], request.get("consent_for"))
                if action == "benchmark_refresh":
                    return {"version": None, "configured": False, "models": [], "error": "benchmark_key_required", "fetched_at": None, "retry_at": 0}
                if action == "credentials":
                    return {"endpoint": "http://127.0.0.1:1/v1", "key": "synthetic-display-only"}
                print(f"Unexpected engine command: {action}", flush=True)
                raise RuntimeError(f"Unexpected engine command: {action}")
            if name == "plugin:autostart|is_enabled":
                return False
            if name == "plugin:event|listen":
                return 1
            if name == "plugin:event|unlisten":
                return None
            print(f"Unexpected native invoke: {name}", flush=True)
            raise RuntimeError(f"Unexpected native invoke: {name}")

        class Assets(SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Assets, directory=str(ROOT / "desktop/dist")))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        origin = f"http://127.0.0.1:{server.server_port}"
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(executable_path="/usr/bin/brave-browser", headless=True, chromium_sandbox=True)
                try:
                    context = await browser.new_context(viewport={"width": 1440, "height": 1050}, color_scheme="light")
                    async def network(route):
                        requests.append(route.request.url)
                        if route.request.url.startswith(origin + "/"):
                            await route.continue_()
                        else:
                            await route.abort()
                    await context.route("**/*", network)
                    page = await context.new_page()
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    await page.expose_binding("nativeReplay", native)
                    await page.add_init_script("""
                        localStorage.setItem('omr:onboarding:v1', JSON.stringify({open:false,step:0}));
                        window.__TAURI_INTERNALS__ = {
                            invoke: (name,args) => window.nativeReplay(name,args),
                            transformCallback: () => 1,
                            unregisterCallback: () => {}
                        };
                        window.__TAURI_EVENT_PLUGIN_INTERNALS__ = { unregisterListener: () => {} };
                    """)
                    await page.goto(origin)
                    await expect(page.locator('.service-strip')).to_be_visible()
                    await expect(page.locator('header .save-state')).to_be_visible()
                    await expect(page.locator('.save-bar')).to_have_count(0)
                    await expect(page.get_by_role('button', name='Ouvrir le Chat', exact=True).first).to_be_visible()
                    await expect(page.locator('.connection-list')).to_contain_text('Aucun fournisseur')
                    await expect(page.locator('.client-access')).not_to_have_attribute('open', '')
                    assert 'credentials' not in calls
                    await page.screenshot(path=str(evidence / 'overview-empty-light.png'), full_page=True)
                    await page.get_by_role('button', name='Ouvrir le Chat', exact=True).first.click()
                    await expect(page.get_by_role('heading', name='Aucun modèle activé')).to_be_visible()
                    await page.get_by_role('button', name='État', exact=True).click()
                    await page.get_by_role('button', name='Ajouter un fournisseur', exact=True).click()
                    await expect(page.get_by_role('heading', name='Ajouter un fournisseur', exact=True)).to_be_visible()
                    await expect(page.get_by_role('combobox', name='Type de fournisseur')).to_be_visible()
                    # Seed only the isolated test engine; no account endpoints or secrets.
                    config = runtime.snapshot()['config']
                    config['connections'] = [{
                        'id': str(uuid.uuid4()), 'name': 'Serveur de test',
                        'url': 'http://127.0.0.1:1/v1',
                        'models': [{
                            'id': str(uuid.uuid4()), 'upstream': 'modele-fixture',
                            'protocols': ['chat'], 'enabled': True, 'tools': False,
                            'quality': 2, 'quality_mode': 'manual',
                            'input_price': None, 'output_price': None, 'effort': None,
                        }],
                    }]
                    runtime.save_config(config, runtime.revision)
                    await page.reload()
                    await expect(page.locator('.connection-list')).to_contain_text('Serveur de test')
                    await expect(page.locator('.service-strip')).to_contain_text('1 modèle')
                    await page.screenshot(path=str(evidence / 'overview-configured-light.png'), full_page=True)
                    # Native disclosure and explicit key access retain separate actions.
                    summary = page.locator('.client-access > summary')
                    await summary.focus()
                    await page.keyboard.press('Enter')
                    await expect(page.get_by_role('button', name='Afficher la clé locale', exact=True)).to_be_visible()
                    assert 'credentials' not in calls
                    await summary.click()
                    # Every destination, dark mode and minimum window remain usable.
                    pages = ['Fournisseurs', 'Chat', 'Profils & règles', 'Stratégies natives', 'Consommation', 'Inspecteur', 'Réglages']
                    for theme in ['light', 'dark']:
                        await page.emulate_media(color_scheme=theme)
                        for destination in pages:
                            advanced = page.locator('.nav-advanced')
                            if destination in ['Profils & règles', 'Stratégies natives', 'Consommation', 'Inspecteur']:
                                if not await advanced.evaluate('(e) => e.open'):
                                    await advanced.locator('summary').click()
                            await page.get_by_role('button', name=destination, exact=True).click()
                            await expect(page.get_by_role('heading', name=destination, exact=True)).to_be_visible()
                            await expect(page.locator('main > [role="alert"]')).to_have_count(0)
                            await page.screenshot(path=str(evidence / f'{theme}-{pages.index(destination)}.png'), full_page=True)
                            assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth'), destination
                        await page.get_by_role('button', name='État', exact=True).click()
                        await page.screenshot(path=str(evidence / f'overview-{theme}.png'), full_page=True)
                    await page.set_viewport_size({'width': 800, 'height': 640})
                    for destination in ['État', 'Fournisseurs', 'Chat', 'Réglages']:
                        await page.get_by_role('button', name=destination, exact=True).click()
                        assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth'), destination
                        await page.screenshot(path=str(evidence / f'minimum-{destination}.png'), full_page=True)
                    await page.set_viewport_size({'width': 1440, 'height': 1050})
                    await page.get_by_role('button', name='État', exact=True).click()
                    fail_snapshot = True
                    await page.get_by_role('button', name='Actualiser', exact=True).click()
                    await expect(page.get_by_role('alert')).to_be_visible()
                    await expect(page.locator('.service-strip')).to_contain_text('Moteur indisponible')
                    await page.screenshot(path=str(evidence / 'engine-error.png'), full_page=True)
                    assert 'credentials' not in calls
                    assert not errors, errors
                    report = {'status': 'pass', 'native_boundary': 'synthetic IPC', 'browser': 'isolated Brave', 'checks': ['empty/configured overview', 'Chat action', 'provider setup navigation', 'keyboard client disclosure', 'no implicit key reveal', 'all screens light/dark', '800x640 no page overflow', 'engine unavailable state', 'no JS errors'], 'external_requests': [u for u in requests if not u.startswith(origin + '/')], 'screenshots': len(list(evidence.glob('*.png')))}
                    assert not report['external_requests'], report
                    (evidence / 'report.json').write_text(json.dumps(report, indent=2))
                    print(json.dumps(report))
                finally:
                    await browser.close()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    asyncio.run(main(Path(sys.argv[1])))
