"""OMP protocol fixtures, not native evidence."""

import unittest

from advanced.codex import StrategyError
from advanced.omp import OMPStrategies


class RPC:
    def __init__(self, response, terminal=None):
        self.response = response
        self.terminal = terminal
        self.calls = []

    def request(self, command, params):
        self.calls.append((command, params))
        return self.response

    def wait(self, predicate, timeout):
        if self.terminal is not None and predicate(self.terminal):
            return self.terminal
        raise TimeoutError()


def response(command, data=None):
    return {
        "type": "response",
        "id": "r",
        "command": command,
        "success": True,
        "data": data,
    }


class OMPContract(unittest.TestCase):
    def test_compact_requires_real_summary_and_boundary(self):
        data = {
            "summary": "synthetic",
            "firstKeptEntryId": "entry",
            "tokensBefore": 123,
        }
        r = RPC(response("compact", data))
        self.assertEqual(OMPStrategies(r).compact(), data)
        self.assertEqual(r.calls, [("compact", {})])
        for data in [None, {}, {"summary": "text"}, {"skipped": True}]:
            with self.assertRaises(StrategyError):
                OMPStrategies(RPC(response("compact", data))).compact()

    def test_turn_waits_for_terminal_matching_request(self):
        end = {"type": "prompt_result", "id": "r", "status": "completed"}
        self.assertEqual(
            OMPStrategies(RPC(response("prompt", {"agentInvoked": True}), end)).turn(
                "synth"
            ),
            end,
        )
        with self.assertRaises(TimeoutError):
            OMPStrategies(
                RPC(response("prompt", {"agentInvoked": True}), {**end, "id": "other"})
            ).turn("synth")

    def test_legacy_ack_without_data_still_requires_terminal(self):
        end = {"type": "prompt_result", "id": "r", "status": "completed"}
        ack = response("prompt")
        ack.pop("data")
        self.assertEqual(OMPStrategies(RPC(ack, end)).turn("synth"), end)
        with self.assertRaises(TimeoutError):
            OMPStrategies(RPC(ack)).turn("synth")

    def test_error_and_abort_are_not_completion(self):
        for status in ["error", "aborted"]:
            with self.assertRaises(StrategyError):
                OMPStrategies(
                    RPC(
                        response("prompt", {"agentInvoked": True}),
                        {"type": "prompt_result", "id": "r", "status": status},
                    )
                ).turn("x")
        with self.assertRaises(StrategyError):
            OMPStrategies(
                RPC(
                    {
                        "type": "response",
                        "id": "r",
                        "command": "compact",
                        "success": False,
                    }
                )
            ).compact()

    def test_switch_checks_provider_and_identity(self):
        r = RPC(response("set_model", {"provider": "p", "id": "m"}))
        OMPStrategies(r).switch("p", "m")
        self.assertEqual(r.calls, [("set_model", {"provider": "p", "modelId": "m"})])
        with self.assertRaises(StrategyError):
            OMPStrategies(
                RPC(response("set_model", {"provider": "p", "id": "other"}))
            ).switch("p", "m")

    def test_cancel_ack_is_not_compute_stop(self):
        r = RPC(response("abort"))
        self.assertEqual(OMPStrategies(r).cancel()["status"], "abort_acknowledged")
        self.assertEqual(r.calls, [("abort", {})])


if __name__ == "__main__":
    unittest.main()
