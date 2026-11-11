"""Behavioral regressions for the independent desktop review. Synthetic only."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from desktop_engine import Runtime, default_config
from test_desktop import connection


class ConsentReviewTest(unittest.TestCase):
    def test_persisted_grant_is_bound_to_exact_destination_on_restart(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(Path(d), "synthetic-key")
            config = default_config()
            c = connection()
            config["connections"] = [c]
            config["decider"] = {
                "connection": c["id"],
                "model": "decider",
                "consent": True,
            }
            target = {"connection": c["id"], "url": c["url"], "model": "decider"}
            runtime.save_config(config, 0, consent_for=target)
            self.assertTrue(
                Runtime(Path(d), "synthetic-key").config["decider"]["consent"]
            )
            path = Path(d, "config.json")
            saved = json.loads(path.read_text())
            saved["config"]["connections"][0]["url"] = "http://127.0.0.1:9998/v1"
            path.write_text(json.dumps(saved))
            # Corrupting the private destination binding now fails closed at startup.
            with self.assertRaisesRegex(ValueError, "^invalid_config$"):
                Runtime(Path(d), "synthetic-key")
            saved["config"] = config
            saved.pop("consent_for", None)
            path.write_text(json.dumps(saved))
            self.assertFalse(
                Runtime(Path(d), "synthetic-key").config["decider"]["consent"]
            )

    def test_config_boolean_cannot_grant_or_restore_destination_consent(self):
        for field in ("url", "model", "connection"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as d:
                runtime = Runtime(Path(d), "synthetic-key")
                config = default_config()
                c = connection()
                other = connection()
                config["connections"] = [c, other]
                config["decider"] = {
                    "connection": c["id"],
                    "model": "decider",
                    "consent": True,
                }
                runtime.save_config(config, 0)
                self.assertFalse(
                    runtime.config["decider"]["consent"], "boolean is not fresh consent"
                )

                def target(cfg):
                    decider = cfg["decider"]
                    conn = next(
                        c
                        for c in cfg["connections"]
                        if c["id"] == decider["connection"]
                    )
                    return {
                        "connection": conn["id"],
                        "url": conn["url"],
                        "model": decider["model"],
                    }

                original_target = target(config)
                runtime.save_config(config, 1, consent_for=original_target)
                self.assertTrue(runtime.config["decider"]["consent"])
                original = copy.deepcopy(runtime.config)
                # Ordinary unrelated edits preserve the existing exact grant.
                config["max_messages"] = 10
                runtime.save_config(config, 2)
                self.assertTrue(runtime.config["decider"]["consent"])
                if field == "url":
                    c["url"] = "http://127.0.0.1:9998/v1"
                    with self.assertRaisesRegex(
                        ValueError, "^credential_destination_changed$"
                    ):
                        runtime.save_config(config, 3, consent_for=original_target)
                    # A new destination requires a fresh vault identity and fresh consent.
                    c["id"] = connection()["id"]
                    config["decider"]["connection"] = c["id"]
                elif field == "model":
                    config["decider"]["model"] = "new-decider"
                else:
                    config["decider"]["connection"] = other["id"]
                # Stale grant cannot authorize a changed endpoint, even via raw IPC.
                runtime.save_config(config, 3, consent_for=original_target)
                self.assertFalse(runtime.config["decider"]["consent"])
                with self.assertRaisesRegex(ValueError, "^decider_not_configured$"):
                    runtime.select(
                        {
                            "model": "omr/economy",
                            "messages": [
                                {"role": "user", "content": "SYNTHETIC-CONSENT-CANARY"}
                            ],
                        },
                        "chat",
                        None,
                        {},
                        None,
                        0,
                    )
                runtime.save_config(config, 4, consent_for=target(config))
                self.assertTrue(runtime.config["decider"]["consent"])
                self.assertTrue(
                    all(
                        not item["config"]["decider"]
                        or not item["config"]["decider"]["consent"]
                        for item in runtime.history
                    )
                )
                # Restoring a previously consented raw configuration cannot revive its grant.
                runtime.save_config(original, 5)
                self.assertFalse(runtime.config["decider"]["consent"])
                restored = Runtime(Path(d), "synthetic-key")
                self.assertFalse(restored.config["decider"]["consent"])
                history_config = next(
                    item["config"]
                    for item in restored.history
                    if item["config"]["decider"]
                )
                restored.save_config(history_config, restored.revision)
                self.assertFalse(restored.config["decider"]["consent"])


class ContinuityReviewTest(unittest.TestCase):
    def test_pins_concrete_route_and_refuses_revoked_or_changed_continuations(self):
        changes = {
            "disabled": lambda c: c["models"][0].update(enabled=False),
            "removed": lambda c: c.update(models=[]),
            "protocol": lambda c: c["models"][0].update(protocols=["responses"]),
            "tools": lambda c: c["models"][0].update(tools=False),
            "url": lambda c: c.update(url="http://127.0.0.1:9998/v1"),
            "upstream": lambda c: c["models"][0].update(upstream="other-model"),
            "effort": lambda c: c["models"][0].update(effort="high"),
            "connection": lambda c: c.update(id=connection()["id"]),
        }
        for reevaluate in (True, False):
            for name, mutate in changes.items():
                with (
                    self.subTest(reevaluate=reevaluate, change=name),
                    tempfile.TemporaryDirectory() as d,
                ):
                    runtime = Runtime(Path(d), "synthetic-key")
                    calls = []

                    def classify(*args):
                        calls.append(True)
                        return {"required_quality": 1, "reason": "simple"}

                    runtime.classifier = classify
                    config = default_config()
                    config["reevaluate"] = reevaluate
                    config["connections"] = [connection(), connection("large", 3, 10)]
                    runtime.save_config(config, 0)
                    payload = {
                        "model": "omr/economy",
                        "tools": [{"type": "function"}],
                        "messages": [{"role": "user", "content": "synthetic"}],
                    }

                    def select():
                        return runtime.select(payload, "chat", "session", {}, None, 0)

                    first = select()
                    if reevaluate:
                        payload["messages"] += [
                            {"role": "assistant", "tool_calls": [{"id": "a"}]},
                            {"role": "tool", "tool_call_id": "a", "content": "result"},
                        ]
                    self.assertEqual(select(), first)
                    self.assertEqual(len(calls), 1)
                    mutate(config["connections"][0])
                    if name == "url":
                        with self.assertRaisesRegex(
                            ValueError, "^credential_destination_changed$"
                        ):
                            runtime.save_config(config, 1)
                        config["connections"][0]["id"] = connection()["id"]
                    runtime.save_config(config, 1)
                    with self.assertRaisesRegex(
                        ValueError, "^continuity_route_unavailable$"
                    ):
                        select()
                    self.assertEqual(
                        len(calls), 1, "must not reclassify a pinned continuation"
                    )
                    # Restoring the original destination is safe; no stale-secret/config aliasing.
                    runtime.save_config(runtime.history[1]["config"], 2)
                    self.assertEqual(select(), first)

    def test_protocol_and_effective_effort_are_pinned_and_tools_remain_required(self):
        for case in ("effort", "protocol", "tools_not_repeated", "no_session"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as d:
                runtime = Runtime(Path(d), "synthetic-key")
                runtime.classifier = lambda *a: {
                    "required_quality": 1,
                    "reason": "simple",
                }
                config = default_config()
                c = connection()
                c["models"][0]["protocols"] = ["chat", "responses"]
                config["connections"] = [c]
                runtime.save_config(config, 0)
                payload = {
                    "model": "omr/economy",
                    "reasoning_effort": "low",
                    "tools": [{"type": "function"}],
                    "messages": [{"role": "user", "content": "synthetic"}],
                }
                runtime.select(payload, "chat", "session", {}, None, 0)
                payload["messages"] += [
                    {"role": "tool", "tool_call_id": "a", "content": "result"}
                ]
                protocol, session = "chat", "session"
                if case == "effort":
                    payload["reasoning_effort"] = "high"
                elif case == "protocol":
                    protocol = "responses"
                    payload["reasoning"] = {"effort": "low"}
                    payload["input"] = [
                        {
                            "type": "function_call_output",
                            "call_id": "a",
                            "output": "result",
                        }
                    ]
                    payload.pop("messages")
                elif case == "tools_not_repeated":
                    payload.pop("tools")
                    c["models"][0]["tools"] = False
                    runtime.save_config(config, 1)
                else:
                    session = None
                with self.assertRaisesRegex(
                    ValueError, "^continuity_route_unavailable$"
                ):
                    runtime.select(payload, protocol, session, {}, None, 0)

    def test_prefill_cannot_hide_tools_in_the_current_logical_turn(self):
        cycles = {
            "anthropic": [
                {"role": "assistant", "content": [{"type": "tool_use", "id": "a"}]},
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "a", "content": "result"}
                    ],
                },
            ],
            "chat": [
                {"role": "assistant", "tool_calls": [{"id": "a"}]},
                {"role": "tool", "tool_call_id": "a", "content": "result"},
            ],
            "responses": [
                {"type": "function_call", "call_id": "a"},
                {"type": "function_call_output", "call_id": "a", "output": "result"},
            ],
        }
        for protocol, cycle in cycles.items():
            for prefill in ("Here is", [{"type": "text", "text": "Here is"}]):
                with self.subTest(protocol=protocol, prefill=prefill):
                    with tempfile.TemporaryDirectory() as d:
                        runtime = Runtime(Path(d), "synthetic-key")
                        calls = []

                        def classify(*args):
                            calls.append(True)
                            return {"required_quality": 1, "reason": "simple"}

                        runtime.classifier = classify
                        config = default_config()
                        config["connections"] = [
                            connection(),
                            connection("large", 3, 10),
                        ]
                        for conn in config["connections"]:
                            conn["models"][0]["protocols"] = [protocol]
                        runtime.save_config(config, 0)
                        messages: list[dict[str, Any]] = [
                            {"role": "user", "content": "synthetic task"}
                        ]
                        field = "input" if protocol == "responses" else "messages"
                        payload = {"model": "omr/economy", field: messages}
                        first = runtime.select(
                            payload, protocol, "session", {}, None, 0
                        )
                        messages.extend(copy.deepcopy(cycle))
                        messages.append({"role": "assistant", "content": prefill})
                        row = {}
                        self.assertEqual(
                            runtime.select(payload, protocol, "session", row, None, 0),
                            first,
                        )
                        self.assertEqual(row["reason"], "tool_continuity")
                        self.assertEqual(len(calls), 1)
                        config["connections"][0]["models"][0]["enabled"] = False
                        runtime.save_config(config, 1)
                        for session in ("session", None):
                            with self.assertRaisesRegex(
                                ValueError, "^continuity_route_unavailable$"
                            ):
                                runtime.select(payload, protocol, session, {}, None, 0)
                        self.assertEqual(len(calls), 1, "no decision after revocation")
                        # Historical tools must not freeze a genuinely new user turn,
                        # even when that new turn also ends with assistant prefill.
                        messages.extend(
                            [
                                {"role": "assistant", "content": "completed"},
                                {"role": "user", "content": "new synthetic task"},
                                {"role": "assistant", "content": prefill},
                            ]
                        )
                        self.assertEqual(
                            runtime.select(payload, protocol, "session", {}, None, 0)[
                                1
                            ]["model"],
                            "large",
                        )
                        self.assertEqual(len(calls), 2)

    def test_assistant_prefill_is_not_a_tool_continuation(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(Path(d), "synthetic-key")
            runtime.classifier = lambda *a: {"required_quality": 1, "reason": "simple"}
            config = default_config()
            config["connections"] = [connection(), connection("large", 3, 10)]
            for conn in config["connections"]:
                conn["models"][0]["protocols"] = ["anthropic"]
            runtime.save_config(config, 0)
            payload = {
                "model": "omr/economy",
                "messages": [
                    {"role": "user", "content": "synthetic task"},
                    {"role": "assistant", "content": "Here is"},
                ],
            }
            self.assertEqual(
                runtime.select(payload, "anthropic", "session", {}, None, 0)[1][
                    "model"
                ],
                "synthetic-small",
            )
            config["connections"][0]["models"][0]["enabled"] = False
            runtime.save_config(config, 1)
            self.assertEqual(
                runtime.select(payload, "anthropic", "session", {}, None, 0)[1][
                    "model"
                ],
                "large",
            )

    def test_actual_tool_calls_and_results_require_the_pinned_route(self):
        for final in (
            {"role": "assistant", "tool_calls": [{"id": "a"}]},
            {"role": "assistant", "function_call": {"name": "synthetic"}},
            {"type": "function_call", "call_id": "a"},
            {"type": "function_call_output", "call_id": "a", "output": "result"},
            {"role": "assistant", "content": [{"type": "tool_use", "id": "a"}]},
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "a", "content": "result"}
                ],
            },
        ):
            with self.subTest(final=final), tempfile.TemporaryDirectory() as d:
                runtime = Runtime(Path(d), "synthetic-key")
                runtime.classifier = lambda *a: {
                    "required_quality": 1,
                    "reason": "simple",
                }
                config = default_config()
                config["connections"] = [connection(), connection("large", 3, 10)]
                runtime.save_config(config, 0)
                payload = {
                    "model": "omr/economy",
                    "messages": [{"role": "user", "content": "synthetic"}],
                }
                runtime.select(payload, "chat", "session", {}, None, 0)
                payload["messages"].append(final)
                self.assertEqual(
                    runtime.select(payload, "chat", "session", {}, None, 0)[1]["model"],
                    "synthetic-small",
                )
                config["connections"][0]["models"][0]["enabled"] = False
                runtime.save_config(config, 1)
                with self.assertRaisesRegex(
                    ValueError, "^continuity_route_unavailable$"
                ):
                    runtime.select(payload, "chat", "session", {}, None, 0)

    def test_new_user_turn_can_reevaluate_after_route_revocation(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = Runtime(Path(d), "synthetic-key")
            runtime.classifier = lambda *a: {"required_quality": 1, "reason": "simple"}
            config = default_config()
            config["connections"] = [connection(), connection("large", 3, 10)]
            runtime.save_config(config, 0)
            payload = {
                "model": "omr/economy",
                "messages": [{"role": "user", "content": "synthetic"}],
            }
            runtime.select(payload, "chat", "session", {}, None, 0)
            config["connections"][0]["models"][0]["enabled"] = False
            runtime.save_config(config, 1)
            self.assertEqual(
                runtime.select(payload, "chat", "session", {}, None, 0)[1]["model"],
                "large",
            )
