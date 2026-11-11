"""OMP 18.13 native RPC strategies, on an already-owned isolated connection."""

from __future__ import annotations

from advanced.codex import StrategyError


class OMPStrategies:
    def __init__(self, rpc, timeout: float = 120):
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.rpc = rpc
        self.timeout = timeout

    def _request(self, command: str, params: dict) -> dict:
        frame = self.rpc.request(command, params)
        if (
            frame.get("type") != "response"
            or frame.get("command") != command
            or frame.get("success") is not True
        ):
            raise StrategyError("native OMP command failed: " + command)
        return frame

    def compact(self, instructions: str | None = None) -> dict:
        params = {} if instructions is None else {"customInstructions": instructions}
        data = self._request("compact", params).get("data")
        if (
            not isinstance(data, dict)
            or not data.get("summary")
            or not data.get("firstKeptEntryId")
            or not isinstance(data.get("tokensBefore"), (int, float))
        ):
            raise StrategyError("native OMP compaction result missing")
        return data

    def switch(self, provider: str, model: str) -> dict:
        data = self._request("set_model", {"provider": provider, "modelId": model}).get(
            "data"
        )
        if (
            not isinstance(data, dict)
            or data.get("provider") != provider
            or data.get("id") != model
        ):
            raise StrategyError("native OMP model identity mismatch")
        return data

    def turn(self, text: str) -> dict:
        ack = self._request("prompt", {"message": text})
        if (ack.get("data") or {}).get("agentInvoked") is False:
            raise StrategyError("OMP did not invoke an agent")
        end = self.rpc.wait(
            lambda e: e.get("type") == "prompt_result" and e.get("id") == ack.get("id"),
            self.timeout,
        )
        if end.get("status") != "completed":
            raise StrategyError("native OMP prompt did not complete successfully")
        return end

    def cancel(self) -> dict:
        self._request("abort", {})
        return {"status": "abort_acknowledged"}
