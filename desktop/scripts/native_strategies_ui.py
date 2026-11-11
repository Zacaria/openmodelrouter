"""Exercise the real Tauri/WebKit controls with a new synthetic native session.

Uses the existing subscription; requires OMR_NATIVE_REPLAY_CONSENT=1.
Run under an isolated HOME/XDG, dbus and Xvfb, with tauri-driver already running.
"""

import json
import os
from pathlib import Path
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

if os.environ.get("OMR_NATIVE_REPLAY_CONSENT") != "1":
    raise SystemExit("Explicit synthetic native replay consent required")
evidence = Path(os.environ["OMR_EVIDENCE"])
evidence.mkdir(parents=True, exist_ok=True)
options = webdriver.common.options.ArgOptions()
options.set_capability(
    "tauri:options", {"application": str(Path(os.environ["OMR_TEST_APP"]).resolve())}
)
options.set_capability("browserName", "wry")
driver = webdriver.Remote(
    command_executor=f"http://127.0.0.1:{os.environ.get('OMR_TEST_DRIVER_PORT', '4444')}",
    options=options,
)
wait = WebDriverWait(driver, 160)
checks = []


def text():
    return driver.find_element(By.TAG_NAME, "body").text


def button(label):
    node = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                f"//button[normalize-space(.)={json.dumps(label, ensure_ascii=False)} or @aria-label={json.dumps(label, ensure_ascii=False)} or (contains(concat(' ',normalize-space(@class),' '),' nav ') and starts-with(normalize-space(.),{json.dumps(label, ensure_ascii=False)}))]",
            )
        )
    )
    driver.execute_script("arguments[0].scrollIntoView({block:'center'})", node)
    node.click()


def ipc(request):
    return driver.execute_async_script(
        "const done=arguments[arguments.length-1];window.__TAURI_INTERNALS__.invoke('engine',{request:arguments[0]}).then(x=>done({ok:x}),e=>done({error:String(e)}));",
        request,
    )


def state():
    return ipc({"command": "snapshot"})["ok"]


def check(name, condition):
    assert condition, name
    checks.append(name)
    print("PASS", name, flush=True)


def finished():
    wait.until(lambda _: not state()["native"]["active"])
    button("Actualiser")
    return state()


def screen(name):
    driver.execute_script("window.scrollTo(0,0)")
    time.sleep(0.25)
    driver.save_screenshot(str(evidence / (name + ".png")))


try:
    wait.until(lambda _: "Moteur disponible" in text())
    driver.set_window_size(1180, 900)
    button("Stratégies natives")
    check(
        "real native page and explicit unavailable clients",
        "Nouvelle session Codex" in text()
        and "préservation des outils et délégation non qualifiées" in text(),
    )
    disabled = driver.find_element(
        By.XPATH, "//button[normalize-space(.)='Connecter une session isolée']"
    )
    check("connect disabled without consent", not disabled.is_enabled())
    screen("01-native-disconnected")
    driver.find_element(
        By.CSS_SELECTOR, "textarea[aria-label='Instructions de session']"
    ).send_keys("Answer in French. Each final response must start exactly RAPPORT:.")
    context = driver.find_element(
        By.CSS_SELECTOR, "textarea[aria-label='Contexte natif']"
    )
    context.send_keys("Public synthetic UI fixture GREEN-FOX-73. Required tag HEAVY.")
    driver.find_element(By.CSS_SELECTOR, "button[role='switch']").click()
    button("Connecter une session isolée")
    s = finished()
    check(
        "UI connects a new real native session",
        s["native"]["status"] == "ready" and not s["native"]["error"],
    )
    prompt = driver.find_element(
        By.CSS_SELECTOR, "textarea[aria-label='Instruction native']"
    )
    prompt.send_keys(
        "For this session answer in French with prefix RAPPORT:. Call read_context once and repeat its fixture and tag. Do not use other tools."
    )
    button("Continuer sans changer")
    s = finished()
    check(
        "UI maintain returns native tool result",
        "GREEN-FOX-73" in text() and s["receipts"][-1]["status"] == "completed",
    )
    prompt.clear()
    prompt.send_keys(
        "Without tools, recall our fixture and tag with the required prefix."
    )
    select = Select(
        driver.find_element(
            By.XPATH,
            "//label[span[normalize-space(.)='Modèle du prochain changement']]//select",
        )
    )
    target = (
        "gpt-6-luna"
        if "gpt-6-luna" in s["native"]["models"]
        else s["native"]["models"][-1]
    )
    select.select_by_value(target)
    button("Changer et envoyer")
    s = finished()
    check(
        "UI model switch confirmed natively",
        s["receipts"][-1]["model_observed"] == target,
    )
    button("Compacter le contexte")
    s = finished()
    check(
        "UI compaction native completion",
        "contextCompaction" in s["receipts"][-1]["native"]["event_types"],
    )
    prompt.clear()
    prompt.send_keys(
        "Delegate to exactly one native child. Give it GREEN-FOX-73 HEAVY and request those words without tools. Wait, integrate and close. Prefix your final answer RAPPORT:."
    )
    button("Déléguer à un enfant")
    s = finished()
    check(
        "UI delegation completed one native child",
        s["receipts"][-1]["native"]["completed_children"] == 1
        and "GREEN-FOX-73" in text(),
    )
    screen("02-native-ready")
    driver.execute_script("window.scrollTo(0,document.body.scrollHeight)")
    time.sleep(0.25)
    driver.save_screenshot(str(evidence / "02b-native-result.png"))
    prompt.clear()
    prompt.send_keys(
        "List 200 detailed synthetic alphabet sorting exercises. Do not use tools."
    )
    button("Continuer sans changer")
    wait.until(lambda _: state()["native"]["active"])
    button("Demander l’annulation")
    s = finished()
    check(
        "UI cancellation waits for interrupted native terminal",
        s["receipts"][-1]["status"] == "cancelled",
    )
    button("Inspecteur")
    check("native operations visible in real inspector", "Session native" in text())
    # Inspect exactly the compaction receipt; opening any row creates a modal.
    rows = driver.find_elements(By.CSS_SELECTOR, "button.receipt")
    compaction = next(node for node in rows if node.text.startswith("compact ·"))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'})", compaction)
    compaction.click()
    check(
        "structured native evidence and unknown costs rendered",
        "contextCompaction" in text() and "Non mesurés · aucun gain présumé" in text(),
    )
    screen("03-native-inspector")
    driver.execute_script(
        "const d=document.querySelector('[role=dialog]');d.scrollTop=d.scrollHeight"
    )
    time.sleep(0.25)
    driver.save_screenshot(str(evidence / "03b-native-costs.png"))
    button("Fermer")
    wait.until(lambda _: not driver.find_elements(By.CSS_SELECTOR, "[role=dialog]"))
    button("Stratégies natives")
    driver.set_window_size(800, 640)
    screen("04-native-small")
    check(
        "small native screen has no horizontal overflow",
        driver.execute_script(
            "return document.documentElement.scrollWidth <= innerWidth"
        ),
    )
    button("Fermer et effacer la session")
    s = finished()
    check(
        "UI closes and clears native context",
        s["native"]["status"] == "disconnected" and not s["native"]["reply"],
    )
finally:
    try:
        if state()["native"]["active"]:
            ipc({"command": "native", "request": {"action": "cancel"}})
            wait.until(lambda _: not state()["native"]["active"])
        ipc({"command": "native", "request": {"action": "close"}})
        wait.until(lambda _: not state()["native"]["active"])
    finally:
        (evidence / "ui-checks.json").write_text(json.dumps(checks, indent=2) + "\n")
        driver.quit()
