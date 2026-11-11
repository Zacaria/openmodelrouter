"""Production UI + real JSONL sidecar/gateway + synthetic provider in Brave.

Run: uv run --with playwright python desktop/scripts/chat_replay.py <evidence-dir>
Tauri invoke is substituted only at the WebView boundary, not the engine/stream.
No personal profile, credentials, paid provider, persistent conversation or app install.
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import threading
import uuid
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from playwright.async_api import async_playwright, expect

from test_desktop_chat import ChatTest
from desktop_engine import decider_identity


async def main(evidence):
    evidence.mkdir(parents=True, exist_ok=True)
    fixture = ChatTest()
    fixture.setUp()
    try:
        with tempfile.TemporaryDirectory(
            prefix="chat-replay-", dir=os.environ.get("TMPDIR")
        ) as home:
            process = await asyncio.to_thread(
                subprocess.Popen,
                (
                    [os.environ["OMR_TEST_ENGINE"], home]
                    if os.environ.get("OMR_TEST_ENGINE")
                    else [sys.executable, str(ROOT / "desktop_sidecar.py"), home]
                ),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=ROOT,
            )
            lock = threading.Lock()
            stdin, stdout, stderr_stream = process.stdin, process.stdout, process.stderr
            assert (
                stdin is not None and stdout is not None and stderr_stream is not None
            )

            def exchange(request):
                with lock:
                    stdin.write(json.dumps(request) + "\n")
                    stdin.flush()
                    result = json.loads(stdout.readline())
                    if "error" in result:
                        raise RuntimeError(result["error"])
                    return result["ok"]

            async def native(_source, command, args):
                if command == "engine":
                    return await asyncio.to_thread(exchange, args["request"])
                if command == "plugin:autostart|is_enabled":
                    return False
                if command == "plugin:event|listen":
                    return 1
                if command == "plugin:event|unlisten":
                    return None
                raise RuntimeError("unsupported_replay_command")

            try:
                initial = exchange(
                    {"command": "init", "key": "synthetic-replay-key-" * 4}
                )
                config = initial["config"]
                # Two explicitly enabled exact destinations, same fixture host.
                c = fixture.c
                c["name"] = "Synthetic Provider"
                c["models"].append(
                    {
                        **c["models"][0],
                        "id": str(uuid.uuid4()),
                        "upstream": "synthetic-second",
                    }
                )
                config["connections"] = [c]
                exchange({"command": "save_config", "config": config, "revision": 0})

                class Assets(SimpleHTTPRequestHandler):
                    def log_message(self, format, *args):
                        pass

                server = ThreadingHTTPServer(
                    ("127.0.0.1", 0),
                    partial(Assets, directory=str(ROOT / "desktop/dist")),
                )
                threading.Thread(target=server.serve_forever, daemon=True).start()
                try:
                    async with async_playwright() as playwright:
                        browser = await playwright.chromium.launch(
                            executable_path=(
                                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
                                if sys.platform == "darwin"
                                else "/usr/bin/brave-browser"
                            ),
                            headless=True,
                            args=["--no-sandbox"],
                        )
                        try:
                            page = await browser.new_page(
                                viewport={"width": 1180, "height": 900}
                            )
                            errors = []
                            page.on(
                                "pageerror", lambda error: errors.append(str(error))
                            )
                            await page.expose_binding("nativeReplay", native)
                            await page.add_init_script("""
                              localStorage.setItem('omr:onboarding:v1', JSON.stringify({open:false,step:0}));
                              window.__TAURI_INTERNALS__ = {
                                invoke: (command,args) => window.nativeReplay(command,args),
                                transformCallback: () => 1,
                                unregisterCallback: () => {},
                              };
                              window.__TAURI_EVENT_PLUGIN_INTERNALS__ = {unregisterListener: () => {}};
                            """)
                            await page.goto(f"http://127.0.0.1:{server.server_port}")
                            await page.get_by_role(
                                "button", name="Chat", exact=True
                            ).click()
                            await expect(
                                page.get_by_role("heading", name="Chat", exact=True)
                            ).to_be_visible()
                            await page.get_by_role(
                                "combobox", name="Modèle du Chat"
                            ).click()
                            await expect(
                                page.locator(".chat-provider-label")
                            ).to_have_text("Synthetic Provider")
                            await page.get_by_role(
                                "option",
                                name="Synthetic Provider · synthetic-exact",
                                exact=True,
                            ).click()
                            await page.locator("textarea").fill("Synthetic first turn")
                            await page.get_by_role(
                                "button", name="Envoyer", exact=True
                            ).click()
                            await expect(page.locator(".chat-status")).to_have_text(
                                "Réponse terminée · identité confirmée"
                            )
                            await expect(
                                page.locator(".chat-assistant")
                            ).to_contain_text("Bonjour 🌲")
                            await page.locator("textarea").fill("Synthetic second turn")
                            await page.get_by_role(
                                "button", name="Envoyer", exact=True
                            ).click()
                            await expect(page.locator(".chat-assistant")).to_have_count(
                                2
                            )
                            await expect(page.locator(".chat-status")).to_have_text(
                                "Réponse terminée · identité confirmée"
                            )
                            assert (
                                len(fixture.calls) == 2
                                and len(fixture.calls[-1][1]["messages"]) == 3
                            )
                            await page.screenshot(
                                path=str(evidence / "chat-two-turns.png"),
                                full_page=True,
                            )

                            await page.get_by_role(
                                "combobox", name="Modèle du Chat"
                            ).click()
                            await page.get_by_role(
                                "option",
                                name="Synthetic Provider · synthetic-second",
                                exact=True,
                            ).click()
                            await expect(page.locator(".chat-message")).to_have_count(0)
                            fixture.mode = "stall"
                            await page.locator("textarea").fill("Synthetic stop test")
                            await page.get_by_role(
                                "button", name="Envoyer", exact=True
                            ).click()
                            await expect(
                                page.locator(".chat-assistant")
                            ).to_contain_text("Bon")
                            await expect(page.locator(".chat-status")).to_have_text(
                                "Réponse en cours…"
                            )
                            await page.screenshot(
                                path=str(evidence / "chat-streaming.png"),
                                full_page=True,
                            )
                            await page.get_by_role(
                                "button", name="Arrêter", exact=True
                            ).click()
                            await expect(page.locator(".chat-status")).to_contain_text(
                                "Génération arrêtée"
                            )
                            assert await asyncio.to_thread(
                                fixture.closed.wait, 2
                            ), "upstream not cancelled"
                            assert (
                                len(fixture.calls[-1][1]["messages"]) == 1
                                and fixture.calls[-1][1]["model"] == "synthetic-second"
                            )
                            await page.screenshot(
                                path=str(evidence / "chat-stopped.png"), full_page=True
                            )

                            fixture.mode = "refused"
                            await page.get_by_role(
                                "button", name="Nouvelle conversation", exact=True
                            ).click()
                            await expect(page.locator(".chat-message")).to_have_count(0)
                            await page.locator("textarea").fill("Synthetic refusal")
                            await page.get_by_role(
                                "button", name="Envoyer", exact=True
                            ).click()
                            await expect(page.locator(".chat-status")).to_contain_text(
                                "a refusé"
                            )
                            await expect(page.locator("textarea")).to_be_disabled()
                            assert (
                                "private-refusal-canary"
                                not in await page.locator("body").inner_text()
                            )
                            await page.screenshot(
                                path=str(evidence / "chat-refused.png"), full_page=True
                            )

                            fixture.mode = "stall"
                            fixture.closed.clear()
                            await page.get_by_role(
                                "button", name="Nouvelle conversation", exact=True
                            ).click()
                            await page.locator("textarea").fill(
                                "Synthetic navigation cancellation"
                            )
                            await page.get_by_role(
                                "button", name="Envoyer", exact=True
                            ).click()
                            await expect(
                                page.locator(".chat-assistant")
                            ).to_contain_text("Bon")
                            await page.get_by_role(
                                "button", name="État", exact=True
                            ).click()
                            assert await asyncio.to_thread(
                                fixture.closed.wait, 2
                            ), "unmount did not cancel upstream"
                            await page.get_by_role(
                                "button", name="Chat", exact=True
                            ).click()
                            await expect(page.locator(".chat-message")).to_have_count(0)
                            await expect(
                                page.get_by_role("combobox", name="Modèle du Chat")
                            ).to_contain_text("Choisir un modèle")
                            storage = await page.evaluate(
                                "JSON.stringify({...localStorage})"
                            )
                            assert "Synthetic first turn" not in storage
                            assert not errors, errors
                            receipts = exchange({"command": "snapshot"})["receipts"]
                            assert len(receipts) == 5
                            assert (
                                receipts[2]["status"]
                                == receipts[4]["status"]
                                == "cancelled"
                            ), [r["status"] for r in receipts]
                            fixture.mode = "complete"
                            snap = exchange({"command": "snapshot"})
                            config = snap["config"]
                            for m in config["connections"][0]["models"]:
                                m["quality"] = 3
                            config["decider"] = {
                                "mode": "server",
                                "protocol": "ollama-systemone",
                                "connection": c["id"],
                                "model": "d3:4b",
                                "consent": True,
                            }
                            exchange(
                                {
                                    "command": "save_config",
                                    "config": config,
                                    "revision": snap["revision"],
                                    "consent_for": decider_identity(config),
                                }
                            )
                            # Remount from the real snapshot rather than fabricate UI state.
                            await page.get_by_role(
                                "button", name="État", exact=True
                            ).click()
                            await page.wait_for_timeout(1200)
                            await page.get_by_role(
                                "button", name="Chat", exact=True
                            ).click()
                            for label in ("Économie", "Équilibré", "Qualité"):
                                await page.get_by_role(
                                    "combobox", name="Modèle du Chat"
                                ).click()
                                await page.get_by_role(
                                    "option", name=f"OMR · {label}", exact=True
                                ).click()
                                await expect(
                                    page.locator(".chat-message")
                                ).to_have_count(0)
                                await expect(
                                    page.locator(".chat-destination")
                                ).to_contain_text("Le profil choisit")
                                for turn in (1, 2):
                                    await page.locator("textarea").fill(
                                        f"Synthetic {label} turn {turn}"
                                    )
                                    await page.get_by_role(
                                        "button", name="Envoyer", exact=True
                                    ).click()
                                    await expect(
                                        page.locator(".chat-status")
                                    ).to_have_text(
                                        "Réponse terminée · identité confirmée"
                                    )
                                    await expect(
                                        page.locator(".chat-assistant")
                                    ).to_have_count(turn)
                                await expect(
                                    page.locator(".chat-receipt")
                                ).to_contain_text("Modèle confirmé")
                            await page.screenshot(
                                path=str(evidence / "chat-profiles.png"), full_page=True
                            )
                            assert len(fixture.decision_calls) == 6
                            receipts = exchange({"command": "snapshot"})["receipts"]
                            assert len(receipts) == 11
                            assert not errors, errors
                            report = {
                                "scope": "Brave production UI / substituted Tauri invoke / real JSONL sidecar and gateway / synthetic provider",
                                "checks": [
                                    "navigation",
                                    "grouped enabled routes",
                                    "useChat two turns",
                                    "visible fragmented streaming",
                                    "stop upstream socket",
                                    "new conversation",
                                    "model switch clears context",
                                    "refusal not success",
                                    "unmount cancels upstream",
                                    "no persistent transcript",
                                    "three automatic profiles with two turns each",
                                    "real synthetic SystemOne decisions",
                                    "eleven real gateway receipts",
                                ],
                                "provider_requests": len(fixture.calls),
                                "decision_requests": len(fixture.decision_calls),
                                "receipt_statuses": [r["status"] for r in receipts],
                                "page_errors": errors,
                            }
                            (evidence / "chat-replay.json").write_text(
                                json.dumps(report, indent=2)
                            )
                            print(json.dumps(report, indent=2))
                        finally:
                            await browser.close()
                finally:
                    server.shutdown()
                    server.server_close()
            finally:
                try:
                    exchange({"command": "shutdown", "force": True})
                    process.wait(timeout=5)
                finally:
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=5)
                    stdin.close()
                    stdout.close()
                    stderr = stderr_stream.read()
                    stderr_stream.close()
                    assert not stderr, stderr
    finally:
        fixture.doCleanups()


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1]).resolve()))
