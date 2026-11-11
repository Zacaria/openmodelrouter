"""Native Linux/WebKit replay against a synthetic local API (no subscriptions).

Run under isolated XDG dirs and dbus/Xvfb; start tauri-driver separately.
OMR_TEST_APP is the exact native binary; OMR_EVIDENCE names ignored output.
"""

import json
import os
from pathlib import Path
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class API(BaseHTTPRequestHandler):
    calls = []
    hold_started = threading.Event()
    hold_release = threading.Event()
    fail_discovery = False

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.fail_discovery:
            self.send_response(503)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        body = json.dumps(
            {"data": [{"id": "synthetic-small"}, {"id": "synthetic-large"}]}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.calls.append(data)
        if "SYNTHETIC-HOLD-QUIT" in json.dumps(data):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            start = {
                "id": "chat_hold",
                "model": data["model"],
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": "Synthetic pending"},
                        "finish_reason": None,
                    }
                ],
            }
            self.wfile.write(b"data: " + json.dumps(start).encode() + b"\n\n")
            self.wfile.flush()
            self.hold_started.set()
            self.hold_release.wait(20)
            terminal = {
                "id": "chat_hold",
                "model": data["model"],
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }
            self.wfile.write(
                b"data: " + json.dumps(terminal).encode() + b"\n\ndata: [DONE]\n\n"
            )
            return
        if data["model"] == "synthetic-decider":
            content = json.dumps(
                {
                    "required_quality": 3 if "COMPLEX" in json.dumps(data) else 1,
                    "reason": "task_requirement",
                }
            )
        else:
            content = "SYNTHETIC-RESPONSE-CANARY"
        body = {
            "model": data["model"],
            "choices": [{"message": {"role": "assistant", "content": content}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "prompt_tokens_details": {"cached_tokens": 10},
                "completion_tokens_details": {"reasoning_tokens": 5},
            },
        }
        encoded = json.dumps(body).encode()
        self.send_response(200)
        if data.get("stream"):
            chunk = {
                "id": "chat_synthetic",
                "model": data["model"],
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": content},
                        "finish_reason": None,
                    }
                ],
            }
            terminal = {
                "id": "chat_synthetic",
                "model": data["model"],
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "usage": body["usage"],
            }
            encoded = (
                b"data: "
                + json.dumps(chunk).encode()
                + b"\n\ndata: "
                + json.dumps(terminal).encode()
                + b"\n\ndata: [DONE]\n\n"
            )
            self.send_header("Content-Type", "text/event-stream")
        else:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


server = ThreadingHTTPServer(("127.0.0.1", 0), API)
threading.Thread(target=server.serve_forever, daemon=True).start()
evidence = Path(os.environ.get("OMR_EVIDENCE", "desktop/.evidence/native"))
evidence.mkdir(parents=True, exist_ok=True)
options = webdriver.common.options.ArgOptions()
options.set_capability(
    "tauri:options", {"application": str(Path(os.environ["OMR_TEST_APP"]).resolve())}
)
options.set_capability("browserName", "wry")
driver_port = int(os.environ.get("OMR_TEST_DRIVER_PORT", "4444"))
driver = webdriver.Remote(
    command_executor=f"http://127.0.0.1:{driver_port}", options=options
)
wait = WebDriverWait(driver, 20)
results = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    results.append(name)
    print("PASS", name, flush=True)


def text():
    return driver.find_element(By.TAG_NAME, "body").text


def button(label):
    element = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                f"//button[normalize-space(.)={json.dumps(label, ensure_ascii=False)} or @aria-label={json.dumps(label, ensure_ascii=False)} or (contains(concat(' ',normalize-space(@class),' '),' nav ') and starts-with(normalize-space(.),{json.dumps(label, ensure_ascii=False)}))]",
            )
        )
    )
    element.click()


def field(label):
    return driver.find_element(
        By.XPATH,
        f"//label[span[normalize-space(.)={json.dumps(label, ensure_ascii=False)}]]//input",
    )


def fill(label, value):
    element = field(label)
    element.clear()
    element.send_keys(value)


def select(label, value):
    field = driver.find_element(
        By.XPATH,
        f"//label[span[normalize-space(.)={json.dumps(label, ensure_ascii=False)}]]",
    )
    option = field.find_element(
        By.XPATH, f".//select/option[@value={json.dumps('value:' + value)}]"
    )
    text = option.get_attribute("textContent")
    field.find_element(By.CSS_SELECTOR, "button[role=combobox]").click()
    wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                f"//*[@role='option'][normalize-space(.)={json.dumps(text, ensure_ascii=False)}]",
            )
        )
    ).click()


def native(request):
    return driver.execute_async_script(
        "const done=arguments[arguments.length-1]; window.__TAURI_INTERNALS__.invoke('engine', {request:arguments[0]}).then(v=>done({ok:v}),e=>done({error:String(e)}));",
        request,
    )


def snapshot():
    return native({"command": "snapshot"})["ok"]


def save():
    wait.until(lambda _: "Réglages enregistrés" in text())
    check(
        "configuration autosaved without engine restart",
        "Réglages enregistrés" in text(),
    )


def screen(name):
    driver.execute_script("window.scrollTo(0,0)")
    driver.execute_async_script(
        "const done=arguments[arguments.length-1]; requestAnimationFrame(()=>requestAnimationFrame(()=>done()));"
    )
    # WebKitGTK's native compositor can lag the DOM after resize/modal changes.
    time.sleep(0.2)
    driver.save_screenshot(str(evidence / f"{name}.png"))


try:
    wait.until(lambda _: "Moteur disponible" in text())
    driver.set_window_size(1180, 820)
    check(
        "initial theme follows system without web persistence",
        driver.execute_script(
            "return document.documentElement.dataset.theme === 'system' && getComputedStyle(document.documentElement).backgroundColor === (matchMedia('(prefers-color-scheme: dark)').matches ? 'rgb(9, 13, 15)' : 'rgb(240, 243, 234)')"
        ),
    )
    if os.environ.get("OMR_TEST_DARK") == "1":
        check(
            "native system dark preference reaches WebKit",
            driver.execute_script(
                'return matchMedia("(prefers-color-scheme: dark)").matches'
            ),
        )
    check(
        "native frozen engine ready and no fabricated usage",
        "REQUÊTES LOCALES" in text(),
    )
    screen("01-overview-empty")
    button("Réglages")
    auto = driver.find_element(
        By.XPATH, "//label[contains(.,'Lancer OMR à l’ouverture de session')]//button"
    )
    if auto.is_enabled():
        auto.click()
        wait.until(
            lambda _: bool(
                list(Path(os.environ["HOME"]).joinpath(".config").rglob("*.desktop"))
            )
        )
        check("autostart writes only isolated HOME configuration", True)
        wait.until(lambda _: auto.is_enabled())
        auto.click()
        wait.until(
            lambda _: (
                not list(
                    Path(os.environ["HOME"]).joinpath(".config").rglob("*.desktop")
                )
            )
        )
        check("autostart disable removes isolated entry", True)
    button("Fournisseurs")
    select("Type de fournisseur", "ollama")
    driver.find_element(
        By.XPATH, "//summary[.='Détails avancés · nouvelle connexion']"
    ).click()
    fill("URL de la nouvelle connexion", f"http://127.0.0.1:{server.server_port}/v1")
    button("Ajouter la connexion")
    driver.find_element(
        By.CSS_SELECTOR, ".connection > .form-grid details > summary"
    ).click()
    check(
        "new connection selects pi-ai without changing saved connections",
        driver.find_element(
            By.XPATH,
            "//label[span[.='Transport fournisseur']]//button[@role='combobox']",
        )
        .get_attribute("textContent")
        .startswith("pi-ai"),
    )
    fill("Nom de la connexion", "API synthétique locale")

    button("Déclarer un modèle")
    fill("Identifiant exact du modèle amont", "synthetic-small")
    check(
        "new manual model is enabled",
        driver.find_element(
            By.XPATH, "//label[contains(.,'Autoriser cette route')]//button"
        ).get_attribute("aria-checked")
        == "true",
    )
    driver.find_element(
        By.XPATH, "//label[contains(.,'Outils compatibles')]//button"
    ).click()
    fill("Entrée · USD / M tokens", "1")
    fill("Sortie · USD / M tokens", "2")
    save()
    port = snapshot()["port"]
    button("Découvrir les modèles")
    wait.until(lambda _: "Catalogue accessible" in text())
    check("discovery makes no generation", len(API.calls) == 0)
    driver.find_element(
        By.XPATH,
        "//label[normalize-space(.)='synthetic-large']//button[@role='checkbox']",
    ).click()
    model = driver.find_elements(By.CSS_SELECTOR, ".model")[-1]
    model.find_element(By.CSS_SELECTOR, "summary").click()
    model.find_element(
        By.XPATH, ".//label[span[.='Qualité déclarée']]//button[@role='combobox']"
    ).click()
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//*[@role='option'][normalize-space(.)='3 · complexe']")
        )
    ).click()
    for label, value in [
        ("Entrée · USD / M tokens", "10"),
        ("Sortie · USD / M tokens", "20"),
    ]:
        element = model.find_element(
            By.XPATH,
            f".//label[span[.={json.dumps(label, ensure_ascii=False)}]]//input",
        )
        element.send_keys(value)
    save()
    check("hot settings keep gateway port", snapshot()["port"] == port)
    test = driver.find_elements(By.XPATH, "//button[normalize-space(.)='Tester']")[0]
    test.click()
    button("Annuler")
    check("cancelled generation test sends nothing", len(API.calls) == 0)
    test.click()
    button("Lancer le test autorisé")
    wait.until(lambda _: "Génération vérifiée" in text())
    check("explicit generation exercises actual gateway", len(API.calls) == 1)
    check(
        "native UI generation traverses pi-ai in the frozen engine",
        snapshot()["receipts"][-1].get("transport") == "pi-ai"
        and API.calls[-1]["stream"] is True,
    )
    screen("02-providers-verified")
    button("Profils & règles")
    config = snapshot()["config"]
    connection = config["connections"][0]
    select("Connexion du décideur", connection["id"])
    fill("Identifiant exact du modèle de décision", "synthetic-decider")
    driver.find_element(
        By.XPATH, "//label[contains(.,'J’autorise l’envoi')]//button"
    ).click()
    select("Modèle de référence", connection["models"][1]["id"])
    save()
    screen("03-profiles")
    credentials = native({"command": "credentials"})["ok"]
    endpoint = credentials["endpoint"] + "/chat/completions"
    session = "11111111-1111-4111-8111-111111111111"

    def gateway(payload, session_id=session):
        request = urllib.request.Request(
            endpoint,
            json.dumps(payload).encode(),
            {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + credentials["key"],
                "X-OMR-Session": session_id,
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read()

    def chat(model, content, stream=False):
        return gateway(
            {
                "model": model,
                "messages": [{"role": "user", "content": content}],
                "stream": stream,
            }
        )

    response = json.loads(chat("omr/economy", "SYNTHETIC-REQUEST-CANARY simple"))
    check(
        "automatic economy selects compatible cheap model",
        response["model"] == "synthetic-small",
    )
    response = json.loads(chat("omr/economy", "COMPLEX SYNTHETIC-REQUEST-CANARY"))
    check(
        "same session reevaluates harder turn", response["model"] == "synthetic-large"
    )
    for profile in ("balanced", "quality"):
        response = json.loads(chat("omr/" + profile, "SYNTHETIC-REQUEST-CANARY simple"))
        check(
            profile + " enforces its declared quality floor",
            response["model"] == "synthetic-large",
        )
    direct = f"direct/{connection['id']}/{connection['models'][0]['id']}"
    before = sum(c["model"] == "synthetic-decider" for c in API.calls)
    check(
        "direct streaming preserves terminal frame",
        b"[DONE]" in chat(direct, "SYNTHETIC-REQUEST-CANARY", True),
    )
    check(
        "direct bypasses decider",
        sum(c["model"] == "synthetic-decider" for c in API.calls) == before,
    )
    # Exercise route revocation through native IPC and the packaged HTTP gateway.
    tool_session = "22222222-2222-4222-8222-222222222222"
    turn = {
        "model": "omr/economy",
        "messages": [{"role": "user", "content": "synthetic tool task"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "synthetic_tool",
                    "parameters": {"type": "object"},
                },
            }
        ],
    }
    check(
        "native tool session starts on small",
        json.loads(gateway(turn, tool_session))["model"] == "synthetic-small",
    )
    turn["messages"] += [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "a",
                    "type": "function",
                    "function": {"name": "synthetic_tool", "arguments": "{}"},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "a", "content": "synthetic result"},
    ]
    count = len(API.calls)
    check(
        "normal native tool continuation keeps route",
        json.loads(gateway(turn, tool_session))["model"] == "synthetic-small"
        and len(API.calls) == count + 1,
    )
    base = snapshot()["config"]
    for name, model_field, value in (
        ("disabled", "enabled", False),
        ("upstream", "upstream", "changed-model"),
        ("effort", "effort", "high"),
    ):
        changed = json.loads(json.dumps(base))
        changed["connections"][0]["models"][0][model_field] = value
        native(
            {
                "command": "save_config",
                "config": changed,
                "revision": snapshot()["revision"],
            }
        )
        count = len(API.calls)
        try:
            gateway(turn, tool_session)
            refused = False
        except urllib.error.HTTPError as error:
            refused = error.code == 400
            error.read()
        wait.until(lambda _: snapshot()["active"] == 0)
        check(
            "native changed continuation refuses without upstream: " + name,
            refused
            and len(API.calls) == count
            and snapshot()["receipts"][-1].get("error")
            == "continuity_route_unavailable",
        )
        native(
            {
                "command": "save_config",
                "config": base,
                "revision": snapshot()["revision"],
            }
        )
    driver.refresh()
    wait.until(lambda _: "Moteur disponible" in text())
    check(
        "native reload preserves gateway after IPC configuration",
        snapshot()["port"] == port,
    )
    # A second real endpoint must receive no context before a fresh exact grant.
    second = ThreadingHTTPServer(("127.0.0.1", 0), API)
    threading.Thread(target=second.serve_forever, daemon=True).start()
    try:
        original_revision = snapshot()["revision"]
        button("Fournisseurs")
        fill(
            "URL API · HTTP ou HTTPS /v1",
            f"http://127.0.0.1:{second.server_port}/v1",
        )
        save()
        count = len(API.calls)
        try:
            chat("omr/economy", "SYNTHETIC-CONSENT-DESTINATION-CANARY")
            refused = False
        except urllib.error.HTTPError as error:
            refused = error.code == 400
            error.read()
        check(
            "changed decider destination refuses context",
            refused and len(API.calls) == count,
        )
        check(
            "engine invalidates consent on destination change",
            not snapshot()["config"]["decider"]["consent"],
        )
        button("Profils & règles")
        consent_switch = lambda: driver.find_element(
            By.XPATH, "//label[contains(.,'J’autorise l’envoi')]//button"
        )
        check(
            "UI invalidates destination grant",
            consent_switch().get_attribute("aria-checked") == "false",
        )
        consent_switch().click()
        save()
        check(
            "fresh destination consent enables automatic request",
            json.loads(chat("omr/economy", "synthetic fresh grant"))["model"]
            == "synthetic-small",
        )
        # Model edits revoke both saved and unsaved grants, even if changed back.
        fill("Identifiant exact du modèle de décision", "other-decider")
        check(
            "model edit clears grant immediately",
            consent_switch().get_attribute("aria-checked") == "false",
        )
        fill("Identifiant exact du modèle de décision", "synthetic-decider")
        check(
            "reverting model edit does not revive grant",
            consent_switch().get_attribute("aria-checked") == "false",
        )
        consent_switch().click()
        save()
        button(f"Restaurer r{original_revision}")
        wait.until(
            lambda _: snapshot()["config"]["connections"][0]["url"] == connection["url"]
        )
        check(
            "restoring configuration revokes historical grant",
            not snapshot()["config"]["decider"]["consent"],
        )
        count = len(API.calls)
        try:
            chat("omr/economy", "SYNTHETIC-CONSENT-RESTORE-CANARY")
            refused = False
        except urllib.error.HTTPError as error:
            refused = error.code == 400
            error.read()
        check(
            "restored destination receives no context before new consent",
            refused and len(API.calls) == count,
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'})", consent_switch()
        )
        screen("08-consent-restored")
    finally:
        second.shutdown()
        second.server_close()
    button("Consommation")
    button("Actualiser")
    wait.until(lambda _: "synthetic-small" in text())
    screen("04-consumption")
    button("Inspecteur")
    wait.until(lambda _: len(driver.find_elements(By.CSS_SELECTOR, ".receipt")) >= 4)
    screen("05-inspector")
    driver.find_elements(By.CSS_SELECTOR, ".receipt")[0].click()
    check(
        "inspector contains no transcript canary",
        "SYNTHETIC-REQUEST-CANARY" not in text()
        and "SYNTHETIC-RESPONSE-CANARY" not in text(),
    )
    screen("06-receipt")
    driver.find_element(By.CSS_SELECTOR, ".dialog .close").click()
    button("Exporter tous les reçus")
    wait.until(lambda _: "Reçus exportés" in text())
    check(
        "native export written",
        bool(list(Path(os.environ["XDG_DATA_HOME"]).rglob("omr-receipts-*.json"))),
    )
    data_config = next(Path(os.environ["XDG_DATA_HOME"]).rglob("config.json"))
    check(
        "native application data directory is private",
        data_config.parent.stat().st_mode & 0o777 == 0o700,
    )
    driver.set_window_size(800, 640)
    screen("07-minimum-window")
    layout = driver.execute_script(
        "return {width:innerWidth, height:innerHeight, bounds:[...document.querySelectorAll('main, .alert, .filters, .receipt')].map(e=>({selector:e.className || e.tagName, left:e.getBoundingClientRect().left, right:e.getBoundingClientRect().right, client:e.clientWidth, scroll:e.scrollWidth}))}"
    )
    (evidence / "minimum-layout.json").write_text(json.dumps(layout, indent=2))
    check(
        "minimum width keeps receipts and notices inside viewport",
        all(
            item["left"] >= 0 and item["right"] <= layout["width"] + 1
            for item in layout["bounds"]
        ),
    )
    check(
        "minimum width has no document overflow",
        driver.execute_script(
            "return document.documentElement.scrollWidth <= window.innerWidth"
        ),
    )
    check(
        "no secrets in webview persistence",
        driver.execute_script(
            "return localStorage.length === 0 && sessionStorage.length === 0"
        ),
    )
    # Programmatic native IPC for conflict and vault failure paths, not claimed as UI typing.
    stale = snapshot()
    changed = native(
        {
            "command": "save_config",
            "config": stale["config"],
            "revision": stale["revision"],
        }
    )
    check("native CAS accepts current revision", "ok" in changed)
    conflict = native(
        {
            "command": "save_config",
            "config": stale["config"],
            "revision": stale["revision"],
        }
    )
    check(
        "native CAS rejects stale revision",
        conflict.get("error") == "configuration_conflict",
    )
    vault = driver.execute_async_script(
        "const done=arguments[arguments.length-1]; window.__TAURI_INTERNALS__.invoke('save_secret',{connection:arguments[0],secret:'SYNTHETIC-VAULT-CANARY'}).then(()=>done('stored'),e=>done(String(e)));",
        connection["id"],
    )
    check("OS vault outcome explicit", vault in ("stored", "vault_unavailable"))
    if os.environ.get("OMR_TEST_UNLOCK_KEYRING") == "1":
        check("synthetic key stored in isolated unlocked OS vault", vault == "stored")
    (evidence / "vault-result.txt").write_text(vault + "\n")
    for path in Path(os.environ["XDG_DATA_HOME"]).rglob("*.json*"):
        check(
            "persisted metadata has no secret/transcript: " + path.name,
            all(
                c not in path.read_text()
                for c in [
                    "SYNTHETIC-VAULT-CANARY",
                    "SYNTHETIC-REQUEST-CANARY",
                    "SYNTHETIC-RESPONSE-CANARY",
                ]
            ),
        )
    if os.environ.get("OMR_TEST_ART_DIRECTION") == "1":
        from visual_replay import verify_presentation

        verify_presentation(driver, evidence, button, select, check, screen)
        button("Fournisseurs")
        API.fail_discovery = True
        button("Découvrir les modèles")
        wait.until(
            lambda _: bool(driver.find_elements(By.CSS_SELECTOR, ".alert.error"))
        )
        wait.until(lambda _: "Découverte échouée" in text())
        check(
            "provider state reflects the failed discovery",
            "Catalogue accessible" not in text(),
        )
        check(
            "real discovery error is visible",
            bool(driver.find_elements(By.CSS_SELECTOR, '.alert.error[role="alert"]')),
        )
        screen("visual-discovery-error")
        API.fail_discovery = False
    button("Quitter OMR Desktop…")
    check(
        "quit requires explicit confirmation", "Arrêter le moteur et quitter" in text()
    )
    for dismissal in ("cancel", "escape", "close"):
        switch = driver.find_element(By.CSS_SELECTOR, '.dialog button[role="switch"]')
        check(
            "fresh quit consent after " + dismissal,
            switch.get_attribute("aria-checked") == "false",
        )
        switch.click()
        if dismissal == "cancel":
            button("Garder OMR ouvert")
        elif dismissal == "escape":
            from selenium.webdriver.common.keys import Keys

            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        else:
            driver.find_element(By.CSS_SELECTOR, ".dialog .close").click()
        wait.until(lambda _: not driver.find_elements(By.CSS_SELECTOR, ".dialog"))
        button("Quitter OMR Desktop…")
        switch = driver.find_element(By.CSS_SELECTOR, '.dialog button[role="switch"]')
        check(
            "dismissal clears forced quit consent: " + dismissal,
            switch.get_attribute("aria-checked") == "false",
        )
    button("Garder OMR ouvert")
    check("cancel quit preserves gateway", snapshot()["port"] == port)
    # A real active request must survive the next unconfirmed quit attempt.
    held_results = []

    def held_request():
        try:
            held_results.append(chat(direct, "SYNTHETIC-HOLD-QUIT", stream=True))
        except Exception:
            held_results.append(None)

    held = threading.Thread(target=held_request, daemon=True)
    held.start()
    check("synthetic streaming request active", API.hold_started.wait(5))
    try:
        button("Quitter OMR Desktop…")
        check(
            "active request needs fresh force consent",
            driver.find_element(
                By.CSS_SELECTOR, '.dialog button[role="switch"]'
            ).get_attribute("aria-checked")
            == "false",
        )
        button("Arrêter le moteur et quitter")
        wait.until(lambda _: "Des requêtes sont en cours" in text())
        check(
            "unconfirmed native quit refuses interruption",
            snapshot()["active"] == 1 and snapshot()["port"] == port,
        )
        wait.until(
            lambda _: (
                "1 requête(s) en cours."
                in driver.find_element(By.CSS_SELECTOR, ".dialog").text
            )
        )
        screen("09-quit-active-refused")
        button("Garder OMR ouvert")
    finally:
        API.hold_release.set()
        held.join(timeout=5)
    check(
        "request finishes without implicit interruption",
        not held.is_alive() and held_results and held_results[0] is not None,
    )
    wait.until(lambda _: snapshot()["active"] == 0)
    # Closing the WebDriver's last window can end its automation session.
    # Exercise the actual window-manager close event and native minimize handler.
    subprocess.run(["wmctrl", "-c", "OMR Desktop"], check=True)
    wait.until(
        lambda _: driver.execute_async_script(
            "const done=arguments[arguments.length-1]; window.__TAURI_INTERNALS__.invoke('plugin:window|is_minimized', {label:'main'}).then(done).catch(()=>done(false));"
        )
    )
    request = urllib.request.Request(
        credentials["endpoint"] + "/models",
        headers={"Authorization": "Bearer " + credentials["key"]},
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        check("closing native window does not stop the gateway", response.status == 200)
    (evidence / "results.json").write_text(
        json.dumps(
            {
                "passes": results,
                "native_binary": os.environ["OMR_TEST_APP"],
                "api_calls": len(API.calls),
                "decisions_before_direct": before,
                "decisions": sum(c["model"] == "synthetic-decider" for c in API.calls),
                "vault": vault,
            },
            indent=2,
        )
    )
except Exception:
    screen("failure")
    (evidence / "failure-dom.txt").write_text(text())
    raise
finally:
    try:
        driver.quit()
    except Exception:
        pass
    server.shutdown()
    server.server_close()
