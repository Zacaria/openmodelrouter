"""Real built Desktop + isolated Runtime persistence in Brave/Linux.

Discovery (604 IDs), generation and vault IPC are synthetic and never call a
provider or the OS vault. This is not a native macOS or credential qualification.
Run after npm run build; uv run --with playwright python scripts/test_provider_ux.py --evidence test-results/provider-ux
"""

import argparse
import copy
import json
import shutil
import sys
import tempfile
import threading
import time

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
from desktop_engine import Runtime  # noqa: E402

CATALOGUE = [f"{'openai' if i % 2 else 'anthropic'}/model-{i}" for i in range(604)]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    checks = []
    with tempfile.TemporaryDirectory(prefix="omr-provider-ux-") as directory:
        runtime = Runtime(Path(directory), "synthetic-" + "x" * 48)
        calls = []
        gate = threading.Event()
        gate.set()
        snapshot_gate = threading.Event()
        snapshot_gate.set()
        snapshot_waiting = threading.Event()
        writes = {"active": 0, "maximum": 0}
        fixture_secrets = {}
        generation_fixture = {"fail": False}
        benchmark_fixture = {"error": "benchmark_key_required"}
        codex_fixture = {"status": "idle", "auth": None, "poll_failure": False, "defer_auth": False}
        portal_fixture = {
            "logging_in": False,
            "running": False,
            "login": None,
            "auth": None,
            "error": None,
        }
        portal_auth = {
            "url": "https://portal.nousresearch.com/oauth/device?user_code=ABCD-EFGH",
            "code": "ABCD-EFGH",
        }
        portal_options = {"defer_auth": False}
        browser_fixture = {"fail": False, "hold_next": False}
        browser_open_gate = threading.Event()
        browser_open_gate.set()
        browser_open_waiting = threading.Event()
        portal_status_gate = threading.Event()
        portal_status_gate.set()
        portal_status_waiting = threading.Event()
        portal_login_gate = threading.Event()
        portal_login_gate.set()
        portal_login_waiting = threading.Event()

        def browser_opens():
            return sum(call["op"] == "open_subscription_login" for call in calls)

        class Handler(SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_POST(self):
                payload = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"]))
                )
                name, data = payload["name"], payload.get("args", {})
                request = data.get("request", {})
                op = request.get("command", name)
                calls.append(
                    {
                        "op": op,
                        "revision": request.get("revision"),
                        "config": copy.deepcopy(request.get("config")),
                        "model": request.get("model"),
                        "action": request.get("action"),
                    }
                )
                try:
                    if op == "snapshot":
                        if not snapshot_gate.is_set():
                            snapshot_waiting.set()
                            if not snapshot_gate.wait(10):
                                raise ValueError("snapshot_fixture_timeout")
                        result = runtime.snapshot()
                    elif op == "save_config":
                        writes["active"] += 1
                        writes["maximum"] = max(writes["maximum"], writes["active"])
                        try:
                            if not gate.wait(10):
                                raise ValueError("fixture_timeout")
                            result = (
                                runtime.reload_config(request["revision"])
                                if request.get("source") == "file"
                                else runtime.save_config(
                                    request["config"],
                                    request["revision"],
                                    request.get("consent_for"),
                                )
                            )
                        finally:
                            writes["active"] -= 1
                    elif op == "discover":
                        assert any(
                            c["id"] == request["connection"]
                            for c in runtime.config["connections"]
                        )
                        result = CATALOGUE
                    elif op == "benchmark_refresh":
                        result = {"version": None, "models": [], "fetched_at": None, "retry_at": 0, "configured": False, **benchmark_fixture}
                    elif op == "save_secret":
                        assert any(
                            c["id"] == data["connection"]
                            for c in runtime.config["connections"]
                        )
                        fixture_secrets[data["connection"]] = data["secret"]
                        result = None
                    elif op == "test_generation":
                        assert request["consent"] is True
                        assert any(
                            request["model"] == f"direct/{c['id']}/{m['id']}"
                            for c in runtime.config["connections"]
                            for m in c["models"]
                        )
                        if generation_fixture["fail"]:
                            runtime.model_states[request["model"].split("/")[-1]] = {
                                "generation": "failed",
                                "generation_diagnostic": {
                                    "code": "generation_budget_exhausted"
                                },
                            }
                            raise ValueError("generation_budget_exhausted")
                        result = {"fixture": True}
                    elif op == "subscription":
                        if request["action"] == "start":
                            codex_fixture.update(
                                status="starting" if codex_fixture["defer_auth"] else "waiting",
                                auth=None if codex_fixture["defer_auth"] else {
                                    "url": "https://auth.openai.com/codex/device",
                                    "code": "TEST-1234",
                                },
                            )
                        elif request["action"] == "cancel":
                            codex_fixture.update(status="cancelled", auth=None)
                        elif request["action"] == "status" and codex_fixture["poll_failure"]:
                            raise ValueError("vault_unavailable")
                        result = {key: copy.deepcopy(codex_fixture[key]) for key in ("status", "auth")}
                    elif op == "portal":
                        if request["action"] == "login":
                            if not portal_login_gate.is_set():
                                portal_login_waiting.set()
                                if not portal_login_gate.wait(10):
                                    raise ValueError("portal_login_fixture_timeout")
                            portal_fixture.update(
                                logging_in=True,
                                auth=None if portal_options["defer_auth"] else copy.deepcopy(portal_auth),
                            )
                        elif request["action"] == "cancel":
                            portal_fixture.update(logging_in=False, auth=None)
                        result = copy.deepcopy(portal_fixture)
                        if request["action"] == "status" and not portal_status_gate.is_set():
                            portal_status_waiting.set()
                            if not portal_status_gate.wait(10):
                                raise ValueError("portal_status_fixture_timeout")
                    elif op == "open_subscription_login":
                        assert set(data) == {"connection"}
                        failed = browser_fixture["fail"]
                        if browser_fixture["hold_next"]:
                            browser_fixture["hold_next"] = False
                            browser_open_waiting.set()
                            if not browser_open_gate.wait(10):
                                raise ValueError("browser_open_fixture_timeout")
                        if failed:
                            raise ValueError("browser_unavailable")
                        result = None
                    elif op == "plugin:event|listen":
                        result = 1
                    elif op == "plugin:autostart|is_enabled":
                        result = False
                    else:
                        raise ValueError("fixture_unsupported_command")
                    response = {"result": result}
                except (ValueError, AssertionError) as error:
                    response = {"error": str(error)}
                body = json.dumps(response).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(Handler, directory=str(ROOT / "dist"))
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    executable_path=shutil.which("brave-browser"),
                    headless=True,
                    chromium_sandbox=True,
                    args=["--disable-gpu"],
                )
                context = browser.new_context(viewport={"width": 1180, "height": 900})
                context.add_init_script("""
                  window.__TAURI_INTERNALS__ = {
                    transformCallback: () => 0, unregisterCallback: () => {},
                    invoke: async (name, args) => { const r = await fetch('/__fixture_ipc', {method:'POST', body:JSON.stringify({name,args})}); const v = await r.json(); if (args?.request?.command === 'portal' && args.request.action === 'status') window.__portalReplies = (window.__portalReplies || 0) + 1; if (args?.request?.command === 'portal' && args.request.action === 'login') window.__portalLoginReplies = (window.__portalLoginReplies || 0) + 1; if (name === 'open_subscription_login') window.__browserReplies = (window.__browserReplies || 0) + 1; if ('error' in v) throw v.error; return v.result; }
                  };
                  window.__TAURI_EVENT_PLUGIN_INTERNALS__ = {unregisterListener: () => {}};
                """)
                page = context.new_page()
                def portal_polls():
                    return sum(call["op"] == "portal" and call["action"] == "status" for call in calls)

                def wait_for_count(counter, expected):
                    deadline = time.monotonic() + 5
                    while counter() < expected and time.monotonic() < deadline:
                        page.wait_for_timeout(50)
                    assert counter() >= expected, {"expected": expected, "observed": counter()}

                def expect_browser_opens(expected):
                    wait_for_count(browser_opens, expected)
                    assert browser_opens() == expected

                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}")
                expect(
                    page.get_by_role("button", name="Visite guidée", exact=True)
                ).to_be_visible()
                tour_titles = [
                    "Vos modèles, au même endroit",
                    "Jev choisit, vos modèles répondent",
                    "Automatique ou modèle imposé",
                    "Utiliser OMR dans oh-my-pi",
                    "Voir ce qui a réellement été exécuté",
                ]
                import re

                for index, title in enumerate(tour_titles):
                    expect(page.get_by_text(title, exact=True)).to_be_visible()
                    page.wait_for_function("""() => {
                        const tooltip = document.querySelector('.react-joyride__tooltip');
                        if (!tooltip) return false;
                        const rect = tooltip.getBoundingClientRect();
                        for (let node = tooltip; node; node = node.parentElement) {
                            if (parseFloat(getComputedStyle(node).opacity) < .99) return false;
                        }
                        return rect.width > 0 && rect.top >= 0 && rect.bottom <= innerHeight && rect.left >= 0 && rect.right <= innerWidth;
                    }""")
                    if index == 0:
                        page.screenshot(path=str(args.evidence / "setup-tour.png"))
                    if index < len(tour_titles) - 1:
                        page.get_by_role("button", name=re.compile(r"^Suivant")).click()
                    else:
                        page.get_by_role(
                            "button", name="Terminer la visite", exact=True
                        ).click()
                assert page.evaluate(
                    "JSON.parse(localStorage.getItem('omr:setup-tour:v1'))"
                ) == {"open": False, "step": 4}
                assert not any(
                    call["op"]
                    in (
                        "save_config",
                        "save_secret",
                        "discover",
                        "test_generation",
                        "test_decision",
                    )
                    for call in calls
                )
                page.get_by_role("button", name="Visite guidée", exact=True).click()
                expect(page.get_by_text(tour_titles[0], exact=True)).to_be_visible()
                page.get_by_role("button", name="Passer la visite", exact=True).click()
                checks.append(
                    "five real setup targets, replay and skip without credential, consent or inference effects"
                )
                page.get_by_role("button", name="Fournisseurs", exact=True).click()
                expect(
                    page.get_by_role(
                        "button", name="Appliquer les réglages", exact=True
                    )
                ).to_have_count(0)
                page.get_by_role("combobox", name="Type de fournisseur").click()
                page.get_by_role("option", name="OpenRouter", exact=True).click()
                page.get_by_text(
                    "Détails avancés · nouvelle connexion", exact=True
                ).click()
                page.get_by_label("URL de la nouvelle connexion").fill(
                    "https://openrouter.ai:443/api/v1"
                )
                page.get_by_role(
                    "button", name="Ajouter la connexion", exact=True
                ).click()
                connection = page.locator(".connection")
                connection.get_by_label(
                    "Clé API · optionnelle pour un serveur local", exact=True
                ).fill("synthetic-vault-canary")
                connection.get_by_role(
                    "button", name="Enregistrer dans le coffre OS", exact=True
                ).click()
                expect(
                    page.get_by_text("Clé enregistrée dans le coffre OS.", exact=True)
                ).to_be_visible()
                assert [
                    c["op"] for c in calls if c["op"] in ("save_config", "save_secret")
                ] == ["save_config", "save_secret"]
                assert (
                    fixture_secrets
                    and "synthetic-vault-canary"
                    not in (Path(directory) / "providers.json").read_text()
                )
                assert (
                    runtime.config["connections"][0]["url"]
                    == "https://openrouter.ai:443/api/v1"
                )
                checks.append(
                    "add → autosave → explicit fixture vault; no Apply; no key in providers.json"
                )

                connection.locator("details").first.locator("summary").click()
                name = connection.get_by_label("Nom de la connexion", exact=True)
                gate.clear()
                name.fill("First write")
                expect(page.get_by_text("Enregistrement…", exact=True)).to_be_visible()
                name.fill("Newer edit")
                name.fill("Latest edit")
                assert name.input_value() == "Latest edit"
                gate.set()
                expect(
                    page.get_by_text("Réglages enregistrés", exact=True)
                ).to_be_visible()
                expect(name).to_have_value("Latest edit")
                assert runtime.config["connections"][0]["name"] == "Latest edit"
                assert writes["maximum"] == 1
                checks.append(
                    "in-flight response preserves newest edits; coalesced serial CAS writes"
                )

                name.fill("OpenRouter fixture")
                connection.get_by_role(
                    "button", name="Découvrir les modèles", exact=True
                ).click()
                catalogue = connection.locator(".model-catalogue")
                expect(catalogue.get_by_role("checkbox")).to_have_count(604)
                expect(
                    catalogue.get_by_text("0 / 604 sélectionnés", exact=True)
                ).to_be_visible()
                scroll = catalogue.get_by_role(
                    "region", name="Résultats du catalogue", exact=True
                )
                assert scroll.evaluate(
                    "e => e.scrollHeight > e.clientHeight && e.clientHeight <= 310"
                )
                checks.append(
                    "real component renders all 604 IDs in bounded scroll region, no truncation"
                )

                # Block the snapshot after a pending draft is discarded.
                url = connection.get_by_label("URL API · HTTP ou HTTPS /v1", exact=True)
                name.fill("discarded fixture")
                checkbox = catalogue.locator("button.checkbox").first
                snapshot_waiting.clear()
                snapshot_gate.clear()
                page.get_by_role(
                    "button", name="Abandonner le brouillon", exact=True
                ).click()
                assert snapshot_waiting.wait(5)
                expect(
                    page.get_by_text("Rechargement de la configuration…", exact=True)
                ).to_be_visible()
                assert checkbox.evaluate("e => !!e.closest('[inert]')")
                assert name.evaluate("e => !!e.closest('[inert]')")
                checkbox.click(force=True, timeout=2000)
                assert checkbox.get_attribute("data-state") == "unchecked"
                snapshot_gate.set()
                expect(
                    page.get_by_text("Brouillon abandonné.", exact=True)
                ).to_be_visible()
                assert checkbox.get_attribute("data-state") == "unchecked"
                checks.append(
                    "discard snapshot barrier prevents catalogue and other configuration edits"
                )

                search = catalogue.get_by_label("Rechercher un modèle", exact=True)
                search.fill("OPENAI/model-1")
                visible_count = catalogue.get_by_role("checkbox").count()
                assert 0 < visible_count < 604
                catalogue.get_by_role(
                    "button", name="Tout sélectionner", exact=True
                ).click()
                expect(catalogue.get_by_role("checkbox", checked=True)).to_have_count(
                    visible_count
                )
                search.fill("anthropic/model-2")
                hidden_count = visible_count
                visible_count = catalogue.get_by_role("checkbox").count()
                catalogue.get_by_role("checkbox").first.focus()
                page.keyboard.press("Space")
                expect(catalogue.get_by_role("checkbox", checked=True)).to_have_count(1)
                catalogue.get_by_role("button", name="Effacer", exact=True).click()
                search.fill("OPENAI/model-1")
                expect(catalogue.get_by_role("checkbox", checked=True)).to_have_count(
                    hidden_count
                )
                search.fill("nothing-matches")
                expect(
                    catalogue.get_by_text(
                        "Aucun résultat pour cette recherche.", exact=True
                    )
                ).to_be_visible()
                expect(
                    catalogue.get_by_role(
                        "button", name="Tout sélectionner", exact=True
                    )
                ).to_be_disabled()
                search.fill("")
                catalogue.get_by_role(
                    "button", name="Tout sélectionner", exact=True
                ).click()
                expect(catalogue.get_by_role("checkbox", checked=True)).to_have_count(
                    604
                )
                expect(
                    page.get_by_text("Réglages enregistrés", exact=True)
                ).to_be_visible()
                assert len(runtime.config["connections"][0]["models"]) == 604
                assert all(
                    m["enabled"] and not m["tools"]
                    for m in runtime.config["connections"][0]["models"]
                )
                assert not runtime.model_states
                assert connection.locator(".model .model-grid").count() == 0
                checks.append(
                    "filtered bulk/clear and keyboard Space preserve hidden selection; all 604 enabled without tools or verification"
                )

                for theme in ("light", "dark"):
                    for width in (800, 1180):
                        page.set_viewport_size({"width": width, "height": 1000})
                        page.evaluate(
                            "theme => document.documentElement.dataset.theme = theme",
                            theme,
                        )
                        catalogue.scroll_into_view_if_needed()
                        assert page.evaluate(
                            "document.documentElement.scrollWidth <= innerWidth"
                        )
                        page.screenshot(
                            path=str(args.evidence / f"catalogue-{theme}-{width}.png")
                        )
                checks.append("light/dark at 800/1180px without horizontal overflow")

                catalogue.get_by_role("button", name="Effacer", exact=True).click()
                search.fill("openai/model-1")
                catalogue.get_by_role("checkbox").first.click()
                model = connection.locator(".model").first
                model.locator("summary").click()
                expect(
                    model.get_by_role("combobox", name="Qualité déclarée", exact=True)
                ).to_have_text("Benchmark externe▾")
                expect(
                    model.get_by_role("combobox", name="Effort transmis", exact=True)
                ).to_contain_text("Client / non imposé")
                model.get_by_label(
                    "Identifiant exact du modèle amont", exact=True
                ).fill("openai/exact-synthetic-model")
                model.get_by_role("button", name="Tester", exact=True).click()
                expect(page.get_by_role("dialog")).to_contain_text(
                    "Elle peut consommer votre quota ou être facturée"
                )
                page.get_by_role(
                    "button", name="Lancer le test autorisé", exact=True
                ).click()
                expect(
                    page.get_by_text(
                        "Génération vérifiée. Reçu disponible dans l’inspecteur.",
                        exact=True,
                    )
                ).to_be_visible()
                success = page.get_by_text("Génération vérifiée. Reçu disponible dans l’inspecteur.", exact=True)
                assert success.evaluate("e => { const r = e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }") , "generation notification is outside the viewport after the scrolled action"
                page.screenshot(path=str(args.evidence / "generation-scrolled.png"))
                checks.append("generation success toast stays inside the viewport after an action below the fold")
                assert [
                    c["op"]
                    for c in calls
                    if c["op"] in ("save_config", "test_generation")
                ][-2:] == ["save_config", "test_generation"]
                checks.append(
                    "expanded real controls preserve quality/empty effort; Tester flushes exact route before explicit fixture generation"
                )

                generation_fixture["fail"] = True
                model.get_by_role("button", name="Tester", exact=True).click()
                page.get_by_role(
                    "button", name="Lancer le test autorisé", exact=True
                ).click()
                diagnostic = "Le test a atteint son plafond de sortie sans réponse complète. La génération n’est pas vérifiée."
                expect(model.get_by_text(diagnostic, exact=True)).to_be_visible()
                page.get_by_role("button", name="Actualiser le classement", exact=True).click()
                expect(page.locator(".toast.error").filter(has_text="Ajoutez votre clé Artificial Analysis")).to_be_visible()
                error_toast = page.locator(".toast.error").filter(has_text=diagnostic)
                expect(error_toast).to_be_visible()
                assert error_toast.evaluate("e => { const r = e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }")
                assert "synthetic-vault-canary" not in page.locator(".toast-viewport").inner_text()
                checks.append("generation failure gets a visible error toast as well as its contextual diagnostic, without secret text")
                checks.append("an unrelated ranking refresh cannot retract a generation action error before its toast duration")
                expect(model.locator("summary")).to_contain_text("Génération échouée")
                page.screenshot(path=str(args.evidence / "generation-diagnostic.png"))
                checks.append(
                    "safe generation fixture code is mapped to French and model state refreshed immediately after refusal"
                )

                url = connection.get_by_label("URL API · HTTP ou HTTPS /v1", exact=True)
                valid = copy.deepcopy(runtime.config)
                url.fill("not-an-url")
                expect(
                    page.get_by_text("Réglages non enregistrés", exact=True)
                ).to_be_visible()
                before = sum(c["op"] == "discover" for c in calls)
                connection.get_by_role(
                    "button", name="Découvrir les modèles", exact=True
                ).click()
                expect(
                    page.get_by_text(
                        "Configuration refusée. Vérifiez les champs, les limites et l’URL API."
                    ).first
                ).to_be_visible()
                assert runtime.config == valid
                assert before == sum(c["op"] == "discover" for c in calls)
                page.get_by_role(
                    "button", name="Abandonner le brouillon", exact=True
                ).click()
                expect(url).to_have_value(valid["connections"][0]["url"])
                checks.append(
                    "real invalid URL refusal preserves last valid config and blocks discovery visibly"
                )

                runtime.save_config(copy.deepcopy(runtime.config), runtime.revision)
                name.fill("Stale revision edit")
                expect(
                    page.get_by_text("Réglages non enregistrés", exact=False)
                ).to_be_visible()
                expect(name).to_have_value("Stale revision edit")
                assert runtime.config == valid
                page.get_by_role(
                    "button", name="Abandonner le brouillon", exact=True
                ).click()
                name.fill("Recovered revision")
                expect(
                    page.get_by_text("Réglages enregistrés", exact=True)
                ).to_be_visible()
                assert runtime.config["connections"][0]["name"] == "Recovered revision"
                valid = copy.deepcopy(runtime.config)
                checks.append(
                    "real stale-revision CAS refuses overwrite; discard refreshes accepted revision and recovers"
                )

                external = copy.deepcopy(runtime.config)
                external["connections"][0]["name"] = "External edit"
                path = Path(directory) / "providers.json"
                external_bytes = json.dumps(external, indent=2)
                path.write_text(external_bytes)
                name.fill("UI conflict")
                expect(
                    page.get_by_text("Réglages non enregistrés", exact=True)
                ).to_be_visible()
                assert path.read_text() == external_bytes
                assert runtime.config == valid
                expect(name).to_have_value("UI conflict")
                page.get_by_role(
                    "button", name="Abandonner le brouillon", exact=True
                ).click()
                expect(
                    page.get_by_text("Brouillon abandonné.", exact=True).last
                ).to_be_visible()
                connection.get_by_role(
                    "button", name="Découvrir les modèles", exact=True
                ).click()
                expect(catalogue.get_by_role("checkbox")).to_have_count(604)
                gate.clear()
                page.get_by_role(
                    "button", name="Charger le fichier", exact=True
                ).click()
                expect(
                    page.get_by_text("Rechargement de la configuration…", exact=True)
                ).to_be_visible()
                assert checkbox.evaluate("e => !!e.closest('[inert]')")
                assert name.evaluate("e => !!e.closest('[inert]')")
                checkbox.click(force=True, timeout=2000)
                assert checkbox.get_attribute("data-state") == "unchecked"
                gate.set()
                expect(name).to_have_value("External edit")
                name.fill("After reload")
                expect(
                    page.get_by_text("Réglages enregistrés", exact=True)
                ).to_be_visible()
                assert runtime.config["connections"][0]["name"] == "After reload"
                checks.append(
                    "real external byte-CAS refuses overwrite, preserves draft, then explicit file reload resumes autosave"
                )
                page.get_by_role("combobox", name="Type de fournisseur").click()
                page.get_by_role(
                    "option", name="Nous Portal · abonnement", exact=True
                ).click()
                page.get_by_role(
                    "button", name="Ajouter la connexion", exact=True
                ).click()
                portal = page.locator('[aria-label="Connexion Nous Portal"]')
                opens_before = browser_opens()
                portal.get_by_role(
                    "button", name="Connecter Nous Portal", exact=True
                ).click()
                expect(portal.get_by_text("ABCD-EFGH", exact=True)).to_be_visible()
                expect_browser_opens(opens_before + 1)
                polls_before = portal_polls()
                wait_for_count(portal_polls, polls_before + 2)
                assert browser_opens() == opens_before + 1
                expect(
                    portal.get_by_role(
                        "button", name="Démarrer le connecteur", exact=True
                    )
                ).to_be_disabled()
                portal.get_by_role(
                    "button", name="Ouvrir la connexion Nous Portal", exact=True
                ).click()
                expect_browser_opens(opens_before + 2)
                page.set_viewport_size({"width": 800, "height": 900})
                portal.scroll_into_view_if_needed()
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                )
                page.screenshot(
                    path=str(args.evidence / "portal-device-instructions.png")
                )
                page.reload()
                page.get_by_role("button", name="Fournisseurs", exact=True).click()
                expect(portal.get_by_text("ABCD-EFGH", exact=True)).to_be_visible()
                polls_before = portal_polls()
                wait_for_count(portal_polls, polls_before + 1)
                assert browser_opens() == opens_before + 2
                portal.get_by_role(
                    "button", name="Annuler la connexion", exact=True
                ).click()
                expect(portal.get_by_text("ABCD-EFGH", exact=True)).to_have_count(0)
                expect(
                    portal.get_by_role(
                        "button", name="Connecter Nous Portal", exact=True
                    )
                ).to_be_enabled()
                assert any(call["op"] == "open_subscription_login" for call in calls)
                assert any(
                    call["op"] == "portal" and call["action"] == "cancel"
                    for call in calls
                )
                checks.append(
                    "Nous explicit login automatically invokes the native opener once; polls and remount never reopen; manual reopening, blocked premature start and cancellation remain available; synthetic auth only"
                )
                portal_options["defer_auth"] = True
                opens_before = browser_opens()
                portal.get_by_role("button", name="Connecter Nous Portal", exact=True).click()
                expect(portal.get_by_role("button", name="Annuler la connexion", exact=True)).to_be_visible()
                expect(portal.get_by_text("ABCD-EFGH", exact=True)).to_have_count(0)
                assert browser_opens() == opens_before
                portal_fixture["auth"] = copy.deepcopy(portal_auth)
                expect(portal.get_by_text("ABCD-EFGH", exact=True)).to_be_visible()
                expect_browser_opens(opens_before + 1)
                portal.get_by_role("button", name="Annuler la connexion", exact=True).click()
                expect(portal.get_by_text("ABCD-EFGH", exact=True)).to_have_count(0)
                checks.append("delayed Nous instructions open the browser only when the native status supplies them; no early open")

                portal_options["defer_auth"] = False
                browser_fixture["fail"] = True
                while page.locator(".toast").count():
                    page.locator(".toast").first.get_by_role("button").click()
                for code in ("benchmark_key_required", "benchmark_access_denied", "benchmark_rate_limited", "benchmark_unavailable"):
                    benchmark_fixture["error"] = code
                    page.get_by_role("button", name="Actualiser le classement", exact=True).click()
                page.set_viewport_size({"width": 400, "height": 360})
                opens_before = browser_opens()
                portal.get_by_role("button", name="Connecter Nous Portal", exact=True).click()
                expect(portal.get_by_role("alert")).to_contain_text("Le navigateur")
                expect(page.locator(".toast.error").filter(has_text="Le navigateur n’a pas pu s’ouvrir")).to_have_count(1)
                polls_before = portal_polls()
                wait_for_count(portal_polls, polls_before + 1)
                assert browser_opens() == opens_before + 1
                expect(portal.get_by_role("alert")).to_contain_text("Le navigateur")
                expect(portal.get_by_text("ABCD-EFGH", exact=True)).to_be_visible()
                browser_fixture["fail"] = False
                portal.get_by_role("button", name="Ouvrir la connexion Nous Portal", exact=True).click()
                expect_browser_opens(opens_before + 2)
                expect(portal.get_by_role("alert")).to_have_count(0)
                expect(page.locator(".toast.error").filter(has_text="Le navigateur n’a pas pu s’ouvrir")).to_have_count(0)
                checks.append("resolving a state-origin browser error retracts its toast as well as the contextual error, without manual dismissal")
                checks.append("with saturated compact notifications, a new browser error is immediately visible and recovery removes it instead of leaving an unseen stale notice")
                page.set_viewport_size({"width": 1180, "height": 1000})
                portal.get_by_role("button", name="Annuler la connexion", exact=True).click()
                expect(portal.get_by_text("ABCD-EFGH", exact=True)).to_have_count(0)
                checks.append("browser failure preserves manual URL/code and cancellation without automatic retries; successful manual reopening clears the browser error")

                portal_options["defer_auth"] = True
                opens_before = browser_opens()
                portal.get_by_role("button", name="Connecter Nous Portal", exact=True).click()
                expect(portal.get_by_role("button", name="Annuler la connexion", exact=True)).to_be_visible()
                portal_status_waiting.clear()
                portal_status_gate.clear()
                portal_fixture["auth"] = copy.deepcopy(portal_auth)
                assert portal_status_waiting.wait(5)
                replies_before = page.evaluate("window.__portalReplies || 0")
                portal.get_by_role("button", name="Annuler la connexion", exact=True).click()
                expect(portal.get_by_role("button", name="Connecter Nous Portal", exact=True)).to_be_enabled()
                portal_status_gate.set()
                page.wait_for_function("n => (window.__portalReplies || 0) > n", arg=replies_before)
                expect(portal.get_by_text("ABCD-EFGH", exact=True)).to_have_count(0)
                assert browser_opens() == opens_before
                checks.append("cancel invalidates a delayed pre-cancel status response: no stale device instructions or browser opening")
                portal_options["defer_auth"] = False
                portal_login_waiting.clear()
                portal_login_gate.clear()
                opens_before = browser_opens()
                portal.get_by_role("button", name="Connecter Nous Portal", exact=True).click()
                assert portal_login_waiting.wait(5)
                portal_status_waiting.clear()
                portal_status_gate.clear()
                assert portal_status_waiting.wait(5)
                portal_login_gate.set()
                expect(portal.get_by_text("ABCD-EFGH", exact=True)).to_be_visible()
                expect_browser_opens(opens_before + 1)
                replies_before = page.evaluate("window.__portalReplies || 0")
                portal_status_gate.set()
                page.wait_for_function("n => (window.__portalReplies || 0) > n", arg=replies_before)
                page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                assert portal.get_by_text("ABCD-EFGH", exact=True).count() == 1, "poll begun during login overwrote the completed action"
                assert browser_opens() == opens_before + 1
                portal.get_by_role("button", name="Annuler la connexion", exact=True).click()
                expect(portal.get_by_text("ABCD-EFGH", exact=True)).to_have_count(0)
                checks.append("status begun during a pending login cannot overwrite its newer completed action")
                browser_fixture.update(fail=True, hold_next=True)
                browser_open_gate.clear()
                browser_open_waiting.clear()
                portal.get_by_role("button", name="Connecter Nous Portal", exact=True).click()
                assert browser_open_waiting.wait(5)
                browser_fixture["fail"] = False
                replies_before = page.evaluate("window.__browserReplies || 0")
                portal.get_by_role("button", name="Ouvrir la connexion Nous Portal", exact=True).click()
                page.wait_for_function("n => (window.__browserReplies || 0) > n", arg=replies_before)
                replies_before = page.evaluate("window.__browserReplies || 0")
                browser_open_gate.set()
                page.wait_for_function("n => (window.__browserReplies || 0) > n", arg=replies_before)
                page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                assert portal.get_by_role("alert").count() == 0, "older browser failure overwrote a successful manual retry"
                portal.get_by_role("button", name="Annuler la connexion", exact=True).click()
                expect(portal.get_by_text("ABCD-EFGH", exact=True)).to_have_count(0)
                checks.append("earlier browser failure cannot restore an error after a newer successful manual retry")
                portal_login_gate.clear()
                portal_login_waiting.clear()
                opens_before = browser_opens()
                replies_before = page.evaluate("window.__portalLoginReplies || 0")
                portal.get_by_role("button", name="Connecter Nous Portal", exact=True).click()
                assert portal_login_waiting.wait(5)
                page.get_by_role("button", name="État", exact=True).click()
                expect(portal).to_have_count(0)
                portal_login_gate.set()
                page.wait_for_function("n => (window.__portalLoginReplies || 0) > n", arg=replies_before)
                page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                assert browser_opens() == opens_before
                page.get_by_role("button", name="Fournisseurs", exact=True).click()
                expect(portal.get_by_text("ABCD-EFGH", exact=True)).to_be_visible()
                assert browser_opens() == opens_before
                portal.get_by_role("button", name="Annuler la connexion", exact=True).click()
                expect(portal.get_by_text("ABCD-EFGH", exact=True)).to_have_count(0)
                checks.append("navigation retires a pending login response; returning shows its status without automatic browser opening")
                page.get_by_role("combobox", name="Type de fournisseur").click()
                page.get_by_role(
                    "option", name="Codex · abonnement ChatGPT", exact=True
                ).click()
                page.get_by_role(
                    "button", name="Ajouter la connexion", exact=True
                ).click()
                codex = page.locator('[aria-label="Connexion Codex"]')
                opens_before = browser_opens()
                codex.get_by_role("button", name="Connecter Codex", exact=True).click()
                expect(codex.get_by_text("TEST-1234", exact=True)).to_be_visible()
                expect_browser_opens(opens_before + 1)
                waiting = codex.get_by_text("Terminez la connexion dans votre navigateur.", exact=True)
                expect(waiting).to_be_visible()
                codex_fixture["poll_failure"] = True
                expect(codex.get_by_role("alert")).to_contain_text("coffre OS")
                codex.screenshot(path=str(args.evidence / "codex-vault-error.png"))
                expect(waiting).to_have_count(0)
                expect(codex.get_by_text("TEST-1234", exact=True)).to_have_count(0)
                expect(codex.get_by_role("button", name="Annuler la connexion", exact=True)).to_be_visible()
                expect(codex.get_by_role("button", name="Connecter Codex", exact=True)).to_be_disabled()
                expect(codex.get_by_role("alert")).not_to_contain_text("La clé n’a pas été enregistrée")
                codex_fixture.update(poll_failure=False, status="connected", auth=None)
                expect(codex.get_by_text("Compte connecté. Découvrez les modèles disponibles.", exact=True)).to_be_visible()
                expect(codex.get_by_role("alert")).to_have_count(0)
                assert sum(call["op"] == "subscription" and call["action"] == "start" for call in calls) == 1
                assert browser_opens() == opens_before + 1
                checks.append("Codex failed vault poll hides stale browser instructions/code, preserves cancellation, then recovers without restarting sign-in; synthetic IPC only")
                codex_fixture["defer_auth"] = True
                opens_before = browser_opens()
                codex.get_by_role("button", name="Changer de compte Codex", exact=True).click()
                expect(codex.get_by_text("Préparation de la connexion…", exact=True)).to_be_visible()
                assert browser_opens() == opens_before
                codex_fixture.update(status="waiting", auth={"url": "https://auth.openai.com/codex/device", "code": "TEST-5678"})
                expect(codex.get_by_text("TEST-5678", exact=True)).to_be_visible()
                expect_browser_opens(opens_before + 1)
                codex.get_by_role("button", name="Annuler la connexion", exact=True).click()
                expect(codex.get_by_text("TEST-5678", exact=True)).to_have_count(0)
                checks.append("delayed Codex instructions open the browser once after status changes from starting to waiting")
                # Exercise toast lifecycle through real UI actions, not a test-only emitter.
                toasts = page.locator(".toast")
                for _ in range(20):
                    if not toasts.count():
                        break
                    toasts.first.get_by_role("button").click()
                expect(toasts).to_have_count(0)
                page.clock.install()
                refresh_benchmark = page.get_by_role("button", name="Actualiser le classement", exact=True)
                refresh_benchmark.click()
                expect(toasts).to_have_count(1)
                page.mouse.move(10, 150)
                page.clock.fast_forward(7000)
                expect(toasts).to_have_count(1)
                page.clock.fast_forward(4000)
                expect(toasts).to_have_count(0)
                checks.append("errors outlast the six-second success duration but expire after ten seconds without blocking later notices indefinitely")
                refresh_benchmark.click()
                expect(toasts).to_have_count(1)
                page.keyboard.press("F8")
                assert page.locator(".toast-viewport").evaluate("e => e.contains(document.activeElement)")
                page.keyboard.press("Escape")
                expect(toasts).to_have_count(0)
                checks.append("errors survive the success timeout; F8 reaches notifications and Escape dismisses them")

                for index, code in enumerate(("benchmark_key_required", "benchmark_access_denied", "benchmark_rate_limited", "benchmark_unavailable")):
                    benchmark_fixture["error"] = code
                    refresh_benchmark.click()
                    expect(toasts).to_have_count(min(3, index + 1))
                expect(page.locator(".toast-viewport")).to_contain_text("1 notification(s) en attente")
                expect(page.locator(".toast-viewport")).to_contain_text("Le benchmark est indisponible")
                checks.append("a fourth error becomes visible immediately rather than waiting behind three earlier errors")
                for theme in ("light", "dark"):
                    page.set_viewport_size({"width": 400, "height": 360})
                    page.evaluate("theme => document.documentElement.dataset.theme = theme", theme)
                    expect(toasts).to_have_count(1)
                    expect(page.locator(".toast-viewport")).to_contain_text("3 notification(s) en attente")
                    expect(page.locator(".toast-viewport")).to_contain_text("Le benchmark est indisponible")
                    assert toasts.evaluate_all("items => items.every(e => { const r = e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight && r.left >= 0 && r.right <= innerWidth; })")
                    assert page.locator(".toast-message").evaluate("e => e.scrollHeight <= e.clientHeight")
                    page.screenshot(path=str(args.evidence / f"toasts-small-{theme}.png"))
                page.set_viewport_size({"width": 1180, "height": 1000})
                expect(toasts).to_have_count(3)
                toasts.filter(has_text="La clé n’a pas accès au catalogue gratuit").get_by_role("button").click()
                expect(toasts).to_have_count(3)
                expect(page.locator(".toast-viewport")).to_contain_text("Le benchmark est indisponible")
                expect(page.locator(".toast-viewport")).to_contain_text("Ajoutez votre clé Artificial Analysis")
                expect(page.locator(".toast-viewport")).not_to_contain_text("notification(s) en attente")
                checks.append("three toasts on tall windows become one fully readable toast at 400×360 in both themes; queued notices survive resizing and dismissal")

                page.set_viewport_size({"width": 1180, "height": 1000})
                page.get_by_role("button", name="Quitter OMR Desktop…", exact=True).click()
                expect(page.get_by_role("dialog")).to_be_visible()
                close_toast = toasts.first.get_by_role("button")
                modal_hit = close_toast.evaluate("e => { const r=e.getBoundingClientRect(), hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2); return {ok:e.contains(hit), rect:{x:r.x,y:r.y,width:r.width,height:r.height},hit:hit?.className,ancestors:[e,e.parentElement,e.parentElement.parentElement,e.parentElement.parentElement.parentElement].map(n=>({tag:n.tagName,cls:n.className,pointer:getComputedStyle(n).pointerEvents,z:getComputedStyle(n).zIndex}))}; }")
                page.screenshot(path=str(args.evidence / "toasts-modal.png"))
                assert modal_hit["ok"], modal_hit
                close_toast.click()
                expect(toasts).to_have_count(2)
                page.get_by_role("button", name="Garder OMR ouvert", exact=True).click()
                while toasts.count():
                    toasts.first.get_by_role("button").click()
                checks.append("toast close remains hit-testable above a modal and does not close or submit that modal")

                generation_fixture["fail"] = False
                model = page.locator(".connection").first.locator(".model").first
                if not model.evaluate("e => e.open"):
                    model.locator("summary").click()
                model.get_by_role("button", name="Tester", exact=True).click()
                page.get_by_role("button", name="Lancer le test autorisé", exact=True).click()
                success = page.locator(".toast.success")
                expect(success).to_have_count(1)
                page.evaluate("scrollTo(0, document.body.scrollHeight)")
                assert page.evaluate("scrollY > 0")
                assert success.evaluate("e => { const r=e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }")
                success.hover()
                page.clock.fast_forward(10000)
                expect(success).to_have_count(1)
                page.mouse.move(10, 150)
                page.clock.fast_forward(6100)
                expect(success).to_have_count(0)
                checks.append("success remains viewport-fixed after further scrolling; hover pauses expiry and leaving resumes its six-second duration")
                assert errors == [], errors
                browser_version = browser.version
                context.close()
                browser.close()
        finally:
            gate.set()
            snapshot_gate.set()
            portal_status_gate.set()
            portal_login_gate.set()
            browser_open_gate.set()
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        report = {
            "scope": "built React app + real isolated Runtime; synthetic catalogue/generation/vault IPC; no provider calls",
            "browser": f"Brave {browser_version}",
            "catalogue_count": len(CATALOGUE),
            "maximum_simultaneous_writes": writes["maximum"],
            "checks": checks,
            "passed": True,
        }
        (args.evidence / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
