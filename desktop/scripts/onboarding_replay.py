"""Isolated real Tauri replay: synthetic APIs + actual pinned ONNX inference.

Run only with disposable HOME/XDG/D-Bus, a matching WebKit driver and
OMR_TEST_APP. No credentials or transcripts are written to evidence.
"""

import hashlib
import json
import os
from pathlib import Path
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class API(BaseHTTPRequestHandler):
    calls = []
    fail = False

    def log_message(self, *_):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.calls.append(
            {
                "path": self.path,
                "model": body.get("model"),
                "authenticated": self.headers.get("Authorization")
                == "Bearer synthetic-onboarding-vault-canary",
            }
        )
        if self.fail:
            self.send_response(503)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path == "/v1/systemone":
            data = {
                "model": "jev-1.13.0",
                "answers": {
                    "route": {
                        "type": "choice",
                        "choice": "reasoning",
                        "probabilities": {"direct": 0.1, "reasoning": 0.9},
                        "confidence": 0.9,
                    }
                },
                "usage": {"input_tokens": 7, "output_tokens": 1},
            }
            if body["model"] == "imajev-2b":
                data = {
                    "model": "imajev-2b",
                    "answers": {
                        "quality": {
                            "type": "choice",
                            "choice": "2",
                            "probabilities": {"1": 0.1, "2": 0.8, "3": 0.1},
                            "confidence": 0.7,
                            "unknown_probability": 0.05,
                            "abstained": False,
                        }
                    },
                }
            raw = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()

        def event(kind, **fields):
            raw = json.dumps({"type": kind, **fields})
            self.wfile.write((f"event: {kind}\ndata: {raw}\n\n").encode())
            self.wfile.flush()

        if self.path == "/v1/chat/completions":
            content = json.dumps({"required_quality": 1, "reason": "simple"})
            for delta, finish in [
                ({"role": "assistant", "content": content}, None),
                ({}, "stop"),
            ]:
                chunk = {
                    "id": "chat_fixture",
                    "model": body["model"],
                    "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 3},
                }
                self.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode())
            self.wfile.write(b"data: [DONE]\n\n")
            return
        assert self.path == "/v1/responses", self.path
        response = {
            "id": "resp_fixture",
            "object": "response",
            "model": body["model"],
            "status": "in_progress",
            "output": [],
        }
        event("response.created", response=response)
        item = {
            "id": "msg_fixture",
            "type": "message",
            "role": "assistant",
            "content": [],
        }
        event("response.output_item.added", output_index=0, item=item)
        event(
            "response.content_part.added",
            output_index=0,
            content_index=0,
            part={"type": "output_text", "text": "", "annotations": []},
        )
        event(
            "response.output_text.delta",
            output_index=0,
            content_index=0,
            item_id=item["id"],
            delta="Synthetic reply",
        )
        item["content"] = [
            {"type": "output_text", "text": "Synthetic reply", "annotations": []}
        ]
        event("response.output_item.done", output_index=0, item=item)
        response.update(
            status="completed",
            output=[item],
            usage={"input_tokens": 7, "output_tokens": 3, "total_tokens": 10},
        )
        event("response.completed", response=response)


root = Path(__file__).resolve().parents[2]
evidence = Path(os.environ["OMR_EVIDENCE"])
evidence.mkdir(parents=True, exist_ok=True)
server = ThreadingHTTPServer(("127.0.0.1", 0), API)
threading.Thread(target=server.serve_forever, daemon=True).start()
results = []
artifacts = []
driver = None


def launch():
    global driver, wait
    options = webdriver.common.options.ArgOptions()
    options.set_capability(
        "tauri:options",
        {"application": str(Path(os.environ["OMR_TEST_APP"]).resolve())},
    )
    options.set_capability("browserName", "wry")
    driver = webdriver.Remote(
        command_executor=f"http://127.0.0.1:{os.environ.get('OMR_TEST_DRIVER_PORT', '4444')}",
        options=options,
    )
    driver.set_script_timeout(35)
    wait = WebDriverWait(driver, 35)
    wait.until(lambda _: "MOTEUR EN SERVICE" in text())


def check(name, condition):
    assert condition, name
    results.append(name)
    print("PASS", name, flush=True)


def text():
    return driver.find_element(By.TAG_NAME, "body").text


def button(label):
    element = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                f"//button[normalize-space(.)={json.dumps(label, ensure_ascii=False)}]",
            )
        )
    )
    element.click()


def field(label, tag="input"):
    return driver.find_element(
        By.XPATH,
        f"//label[span[normalize-space(.)={json.dumps(label, ensure_ascii=False)}]]//{tag}",
    )


def fill(label, value):
    element = field(label)
    element.clear()
    element.send_keys(value)


def select(label, value):
    Select(field(label, "select")).select_by_value(value)


def switch(label):
    driver.find_element(
        By.XPATH,
        f"//label[normalize-space(.)={json.dumps(label, ensure_ascii=False)}]//button[@role='switch']",
    ).click()


def native(request):
    result = driver.execute_async_script(
        "const done=arguments[arguments.length-1];window.__TAURI_INTERNALS__.invoke('engine',{request:arguments[0]}).then(ok=>done({ok}),e=>done({error:String(e)}));",
        request,
    )
    if "error" in result:
        raise AssertionError(result["error"])
    return result["ok"]


def snapshot():
    return native({"command": "snapshot"})


def screen(name):
    driver.save_screenshot(str(evidence / f"{name}.png"))
    (evidence / f"{name}.txt").write_text(text())


def stored():
    return [
        path
        for path in Path(os.environ["XDG_DATA_HOME"]).rglob("config.json")
        if path.parent.name == "io.havesomecode.omr"
    ]


def managed_pids():
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / "cmdline").read_bytes()
            if (
                b"--managed-worker" in command
                and os.environ["XDG_DATA_HOME"].encode() in command
            ):
                found.append(int(entry.name))
        except (OSError, ProcessLookupError):
            pass
    return found


def save_decider():
    before = snapshot()["revision"]
    button("Enregistrer le décideur et continuer")
    wait.until(lambda _: snapshot()["revision"] > before)
    return snapshot()


def test_decider():
    before = len(snapshot()["receipts"])
    button("Tester le décideur · coût API possible")
    wait.until(lambda _: len(snapshot()["receipts"]) > before)
    row = snapshot()["receipts"][-1]
    check("explicit decision test succeeds " + str(len(results)), row["status"] == "ok")
    return row


try:
    launch()
    check(
        "empty state opens resumable onboarding",
        "Brancher OMR, à votre rythme" in text(),
    )
    check("empty render performs zero upstream calls", API.calls == [])
    button("Continuer en accès direct")
    check(
        "onboarding can be skipped without a decider",
        "Brancher OMR, à votre rythme" not in text(),
    )
    button("Reprendre la configuration")
    fill("Nom de la connexion guidée", "Fixture locale")
    fill("URL API du parcours guidé", f"http://127.0.0.1:{server.server_port}/v1")
    fill("Modèle répondant · identifiant exact", "synthetic-responder")
    fill(
        "Clé API guidée · facultative pour localhost",
        "synthetic-onboarding-vault-canary",
    )
    button("Enregistrer le répondant")
    wait.until(lambda _: "Mode du décideur" in text())
    state = snapshot()
    check(
        "respondent saved with Responses and pi-ai",
        state["config"]["connections"][0]["transport"] == "pi-ai"
        and state["config"]["connections"][0]["models"][0]["protocols"]
        == ["responses"],
    )
    check(
        "OS vault stores only selected synthetic connection",
        state["secret_states"] == [state["config"]["connections"][0]["id"]],
    )
    check("saving and navigating perform no inference", API.calls == [])
    conn = state["config"]["connections"][0]["id"]
    driver.quit()
    driver = None
    time.sleep(2)
    launch()
    check(
        "interrupted first run automatically resumes the decider step",
        "Brancher OMR, à votre rythme" in text() and "Mode du décideur" in text(),
    )
    check("resume never repeats inference", API.calls == [])
    select("Mode du décideur", "server")
    fill("Identifiant exact du modèle de décision", "synthetic-decider")
    switch("J’autorise l’envoi de l’extrait de contexte à ce décideur")
    save_decider()
    button("Enregistrer le routage")
    check("explicit test step performs zero automatic inference", API.calls == [])
    button("Tester")
    wait.until(
        lambda _: (
            snapshot()["model_states"]
            and any(
                v.get("generation") == "verified"
                for v in snapshot()["model_states"].values()
            )
        )
    )
    check(
        "real gateway generation uses Responses through actual pi-ai",
        API.calls[-1]["path"] == "/v1/responses" and API.calls[-1]["authenticated"],
    )
    button("2. Décideur")
    test_decider()
    check(
        "URL mode uses real pi-ai Chat adapter",
        API.calls[-1]["path"] == "/v1/chat/completions",
    )
    before = len(API.calls)
    select("Mode du décideur", "byok")
    check(
        "mode change revokes draft consent",
        driver.find_element(
            By.XPATH, "//label[contains(.,'J’autorise l’envoi')]//button"
        ).get_attribute("aria-checked")
        == "false",
    )
    fill("Identifiant exact du modèle de décision", "synthetic-decider")
    switch("J’autorise l’envoi de l’extrait de contexte à ce décideur")
    save_decider()
    button("2. Décideur")
    test_decider()
    check(
        "BYOK uses vault key once without retry",
        len(API.calls) == before + 1 and API.calls[-1]["authenticated"],
    )
    API.fail = True
    before = len(API.calls)
    before_receipts = len(snapshot()["receipts"])
    button("Tester le décideur · coût API possible")
    wait.until(lambda _: len(snapshot()["receipts"]) > before_receipts)
    check(
        "upstream refusal creates failed receipt without retry",
        snapshot()["receipts"][-1]["status"] == "failed"
        and len(API.calls) == before + 1,
    )
    API.fail = False
    test_decider()
    select("Protocole du décideur", "jev")
    switch("J’autorise l’envoi de l’extrait de contexte à ce décideur")
    save_decider()
    button("2. Décideur")
    row = test_decider()
    check(
        "Jev uses SystemOne and actual choice decoder",
        API.calls[-1]["path"] == "/v1/systemone" and row["required_quality"] == 3,
    )
    select("Protocole du décideur", "imajev")
    fill("Identifiant exact du modèle de décision", "imajev-2b")
    switch("J’autorise l’envoi de l’extrait de contexte à ce décideur")
    save_decider()
    button("2. Décideur")
    row = test_decider()
    check(
        "Imajev synthetic protocol uses typed readout response, never chat",
        API.calls[-1]["path"] == "/v1/systemone"
        and row["required_quality"] == 2
        and row["decision_usage"] == {},
    )
    screen("01-three-modes")
    select("Mode du décideur", "managed")
    switch("J’autorise la classification locale par ce checkpoint s1d1")
    save_decider()
    button("2. Décideur")
    before = len(API.calls)
    switch("J’autorise le téléchargement des poids publics s1d1 sur cet appareil")
    button("Télécharger et vérifier s1d1")
    wait.until(lambda _: snapshot()["managed"]["active"])
    button("Annuler")
    wait.until(lambda _: not snapshot()["managed"]["active"])
    check(
        "native cancellation leaves no partial checkpoint or live downloader",
        snapshot()["managed"]["status"] == "cancelled"
        and not list(Path(os.environ["XDG_DATA_HOME"]).rglob(".managed-*")),
    )
    switch("J’autorise le téléchargement des poids publics s1d1 sur cet appareil")
    button("Télécharger et vérifier s1d1")
    WebDriverWait(driver, 330).until(
        lambda _: snapshot()["managed"]["status"] in ("installed", "error")
    )
    check(
        "native frozen sidecar downloads and verifies full actual checkpoint",
        snapshot()["managed"]["status"] == "installed",
    )
    check(
        "download does not start inference or send API prompts",
        len(API.calls) == before and not snapshot()["managed"]["running"],
    )
    button("Démarrer le modèle géré")
    wait.until(lambda _: snapshot()["managed"]["status"] in ("ready", "error"))
    check(
        "frozen sidecar starts actual ONNX CPU decoder without user Python",
        snapshot()["managed"]["running"],
    )
    row = test_decider()
    check(
        "real local classification reports actual tokenizer count",
        row["decision_usage"]["input_tokens"] == 9
        and row["decision_usage"]["output_tokens"] == 0
        and row["required_quality"] == 1,
    )
    credentials = native({"command": "credentials"})
    qualities = []
    for prompt in (
        "What is the capital of France?",
        "Prove that the set of prime numbers is infinite.",
    ):
        before_rows = len(snapshot()["receipts"])
        request = urllib.request.Request(
            credentials["endpoint"] + "/responses",
            json.dumps(
                {"model": "omr/economy", "input": prompt, "max_output_tokens": 16}
            ).encode(),
            {
                "Authorization": "Bearer " + credentials["key"],
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            generated = json.loads(response.read())
        check(
            "managed decision routes to actual configured respondent "
            + str(len(results)),
            generated["model"] == "synthetic-responder",
        )
        wait.until(lambda _: len(snapshot()["receipts"]) > before_rows)
        qualities.append(snapshot()["receipts"][-1]["required_quality"])
    check("native managed classifier is not constant", qualities == [1, 2])
    screen("02-managed-ready")
    owned = managed_pids()
    check("native frozen managed process tree is observable", bool(owned))
    button("Arrêter le modèle géré")
    wait.until(lambda _: not snapshot()["managed"]["running"])
    check(
        "explicit stop reaps managed process",
        snapshot()["managed"]["status"] == "stopped",
    )
    wait.until(lambda _: not managed_pids())
    check("stop reaps both bootloader and ONNX child", not managed_pids())
    config_before = snapshot()["config"]
    button("Continuer en accès direct")
    check(
        "receipts never contain prompts or keys",
        all(
            s not in json.dumps(snapshot()["receipts"])
            for s in (
                "capital of France",
                "prime numbers",
                "vault-canary",
                "Synthetic reply",
            )
        ),
    )
    persisted = stored()
    check("config is persisted in isolated application data", len(persisted) == 1)
    check(
        "configuration never stores key", "vault-canary" not in persisted[0].read_text()
    )
    driver.quit()
    driver = None
    time.sleep(2)
    launch()
    state = snapshot()
    check(
        "restart restores exact useful configuration", state["config"] == config_before
    )
    check(
        "existing valid configuration is not forced through onboarding",
        "Brancher OMR, à votre rythme" not in text(),
    )
    check(
        "restart never auto-starts managed process",
        state["managed"]["status"] == "installed" and not state["managed"]["running"],
    )
    check(
        "restart reloads synthetic key from OS vault", state["secret_states"] == [conn]
    )
    button("Reprendre la configuration")
    check("assistant can resume persisted choices", "3. Routage" in text())
    screen("03-resumed")
    (evidence / "results.json").write_text(
        json.dumps(
            {
                "passes": results,
                "native_binary_sha256": hashlib.sha256(
                    Path(os.environ["OMR_TEST_APP"]).read_bytes()
                ).hexdigest(),
                "api_calls": API.calls,
                "managed_checkpoint": state["managed"]["checkpoint"],
                "native_required_qualities": qualities,
                "real_providers": [],
                "qualified_os": "Linux x86_64",
                "unqualified_os": ["macOS", "Windows"],
            },
            indent=2,
        )
    )
except Exception:
    if driver:
        screen("failure")
        (evidence / "failure-state.json").write_text(json.dumps(snapshot(), indent=2))
    raise
finally:
    if driver:
        driver.quit()
    server.shutdown()
    server.server_close()
