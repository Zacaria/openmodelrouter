"""Synthetic contract checks; live source qualification needs a native API key."""

import copy
import http.client
import json
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import desktop_benchmarks as benchmark


def fixture():
    return {
        "intelligence_index_version": 5,
        "tier": "free",
        "pagination": {"page": 1, "page_size": 3, "total_pages": 1, "has_more": False},
        "data": [
            {
                "slug": name,
                "name": name,
                "evaluations": {"artificial_analysis_intelligence_index": score},
            }
            for name, score in [("small", 10), ("middle", 30), ("large", 60)]
        ],
    }


class Benchmarks(unittest.TestCase):
    def test_download_combines_every_page_before_computing_tiers(self):
        paths = []
        mode = ["ok"]

        class Pages(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_GET(self):
                if mode[0] == "trickle":
                    try:
                        self.wfile.write(b"HTTP/1.1 200 OK\r\nX-Slow: ")
                        for _ in range(100):
                            self.wfile.write(b"x")
                            self.wfile.flush()
                            time.sleep(0.03)
                    except OSError:
                        pass
                    return
                paths.append(self.path)
                page = 2 if self.path.endswith("page=2") else 1
                data = fixture()
                if mode[0] == "version" and page == 2:
                    data["intelligence_index_version"] = 6
                data["data"] = data["data"][:2] if page == 1 else data["data"][2:]
                if mode[0] == "unscored" and page == 1:
                    for row in data["data"]:
                        row["evaluations"]["artificial_analysis_intelligence_index"] = None
                data["pagination"] = {
                    "page": page,
                    "page_size": 2,
                    "total_pages": 2,
                    "has_more": page == 1,
                }
                body = json.dumps(data).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                if (mode[0] == "quota-first" and page == 1) or (
                    mode[0] == "quota-last" and page == 2
                ):
                    self.send_header("X-RateLimit-Remaining", "0")
                    self.send_header("X-RateLimit-Reset", "100000000000")
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Pages)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with patch.object(
                benchmark.http.client,
                "HTTPSConnection",
                side_effect=lambda *a, **kw: http.client.HTTPConnection(
                    "127.0.0.1", server.server_port, timeout=1
                ),
            ):
                data = benchmark.parse(benchmark.download("synthetic-key"))
                mode[0] = "unscored"
                unscored = benchmark.parse(benchmark.download("synthetic-key"))
                self.assertEqual([m["quality"] for m in unscored["models"]], [0, 0, 2])
                mode[0] = "version"
                with self.assertRaises(ValueError):
                    benchmark.download("synthetic-key")
                self.assertEqual(
                    paths, [benchmark.ENDPOINT, benchmark.ENDPOINT + "?page=2"] * 3
                )
                mode[0] = "quota-first"
                with tempfile.TemporaryDirectory() as directory:
                    limited = benchmark.refresh(Path(directory), "synthetic-key")
                    self.assertEqual(limited["error"], "benchmark_rate_limited")
                    self.assertEqual(limited["models"], [])
                    self.assertEqual(len(paths), 7)
                    benchmark.refresh(Path(directory), "synthetic-key", force=True)
                    self.assertEqual(len(paths), 7)
                mode[0] = "quota-last"
                with tempfile.TemporaryDirectory() as directory:
                    fresh = benchmark.refresh(Path(directory), "synthetic-key")
                    self.assertIsNone(fresh["error"])
                    self.assertEqual(len(fresh["models"]), 3)
                    self.assertEqual(fresh["retry_at"], 100000000000)
                    self.assertEqual(len(paths), 9)
                    limited = benchmark.refresh(Path(directory), "synthetic-key", force=True)
                    self.assertEqual(limited["error"], "benchmark_rate_limited")
                    self.assertEqual(limited["models"], fresh["models"])
                    self.assertEqual(len(paths), 9)
                mode[0] = "trickle"
                started = time.monotonic()
                with (
                    patch.object(benchmark, "TIMEOUT", 0.2),
                    self.assertRaises((OSError, http.client.HTTPException, ValueError)),
                ):
                    benchmark.download("synthetic-key")
                self.assertLess(time.monotonic() - started, 1)
            self.assertEqual([m["quality"] for m in data["models"]], [1, 2, 3])
            self.assertEqual(len(paths), 9)
        finally:
            server.shutdown()
            server.server_close()

    def test_native_selection_never_trusts_an_unverified_frontend_tier(self):
        data = {m["slug"]: m for m in benchmark.parse(fixture())["models"]}
        model = {"upstream": "large", "quality": 3, "quality_mode": "benchmark"}
        self.assertEqual(benchmark.effective_quality(model, data), 3)
        self.assertEqual(benchmark.effective_quality(model, {}), 0)
        self.assertEqual(benchmark.effective_quality({**model, "quality": 2}, data), 0)
        self.assertEqual(
            benchmark.effective_quality({**model, "quality_mode": "manual"}, {}), 3
        )
        from desktop_engine import Runtime, default_config
        from test_desktop import connection

        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(directory), "synthetic-gateway-key-" * 4)
            config = default_config()
            config["connections"] = [connection("large", quality=3)]
            config["connections"][0]["models"][0]["quality_mode"] = "benchmark"
            runtime.save_config(config, 0)
            self.assertEqual(runtime.routes()[0][2]["quality"], 0)
            runtime.benchmark_data = benchmark.parse(fixture())
            self.assertEqual(runtime.routes()[0][2]["quality"], 3)
            runtime.benchmark_data = {"models": []}
            self.assertEqual(runtime.routes()[0][2]["quality"], 0)
            self.assertEqual(
                runtime.config["connections"][0]["models"][0]["quality"], 3
            )
            self.assertTrue(runtime.catalogue()["data"][-1]["id"].startswith("direct/"))

    def test_model_rename_requires_a_fresh_explicit_benchmark_association(self):
        from desktop_engine import Runtime, default_config
        from test_desktop import connection

        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(directory), "synthetic-gateway-key-" * 4)
            config = default_config()
            config["connections"] = [connection("private-A", quality=3)]
            model = config["connections"][0]["models"][0]
            model.update(quality_mode="benchmark", benchmark_model="large")
            runtime.save_config(config, 0)
            runtime.benchmark_data = benchmark.parse(fixture())
            self.assertEqual(runtime.routes()[0][2]["quality"], 3)
            model["upstream"] = "private-B"
            with self.assertRaisesRegex(ValueError, "invalid_config"):
                runtime.save_config(config, 1)
            self.assertEqual(runtime.revision, 1)
            model.update(benchmark_model="", quality=0)
            runtime.save_config(config, 1)
            self.assertEqual(runtime.routes()[0][2]["quality"], 0)
            model.update(benchmark_model="large", quality=3)
            runtime.save_config(config, 2)
            self.assertEqual(runtime.routes()[0][2]["quality"], 3)

    def test_invalid_complete_catalogue_preserves_successful_response_quota(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            payload = fixture()
            for row in payload["data"]:
                row["evaluations"]["artificial_analysis_intelligence_index"] = None
            payload["_retry_at"] = time.time() + 1000
            with patch.object(benchmark, "download", return_value=payload) as fetch:
                invalid = benchmark.refresh(home, "synthetic-key", force=True)
                self.assertEqual(invalid["error"], "benchmark_unavailable")
                self.assertEqual(invalid["retry_at"], payload["_retry_at"])
                self.assertEqual(invalid["models"], [])
                limited = benchmark.refresh(home, "synthetic-key", force=True)
                self.assertEqual(limited["error"], "benchmark_rate_limited")
                self.assertEqual(fetch.call_count, 1)
                cached = json.loads((home / "benchmark-artificial-analysis.json").read_text())
                self.assertEqual(cached["retry_at"], payload["_retry_at"])

    def test_quota_without_any_cached_scores_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                benchmark, "download", side_effect=benchmark.Quota(100000000000)
            ) as fetch:
                self.assertEqual(
                    benchmark.refresh(Path(directory), "synthetic-key")["error"],
                    "benchmark_rate_limited",
                )
                self.assertEqual(
                    benchmark.refresh(Path(directory), "synthetic-key", force=True)[
                        "error"
                    ],
                    "benchmark_rate_limited",
                )
                self.assertEqual(fetch.call_count, 1)

    def test_source_scores_tiers_and_ties(self):
        result = benchmark.parse(fixture())
        self.assertEqual(result["version"], "5")
        self.assertEqual([r["quality"] for r in result["models"]], [1, 2, 3])
        same = fixture()
        for row in same["data"]:
            row["evaluations"]["artificial_analysis_intelligence_index"] = 20
        self.assertEqual(
            [r["quality"] for r in benchmark.parse(same)["models"]], [2] * 3
        )
        same["data"][0]["evaluations"]["artificial_analysis_intelligence_index"] = None
        self.assertEqual(benchmark.parse(same)["models"][0]["quality"], 0)

    def test_invalid_source_never_produces_a_partial_ranking(self):
        bad = []
        for value in [float("nan"), float("inf"), True, "60"]:
            data = fixture()
            data["data"][-1]["evaluations"][
                "artificial_analysis_intelligence_index"
            ] = value
            bad.append(data)
        data = fixture()
        data["data"].append(copy.deepcopy(data["data"][0]))
        bad.extend([data, {**fixture(), "has_more": True}, {"data": fixture()["data"]}])
        bad.append(
            {
                **fixture(),
                "pagination": {
                    "page": 1,
                    "page_size": 3,
                    "total_pages": 2,
                    "has_more": True,
                },
            }
        )
        for data in bad:
            with self.subTest(data=data), self.assertRaises(ValueError):
                benchmark.parse(data)

    def test_cache_missing_key_refresh_failure_and_backoff(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with patch.object(benchmark, "download", return_value=fixture()) as fetch:
                self.assertEqual(
                    benchmark.refresh(path, None)["error"], "benchmark_key_required"
                )
                fetch.assert_not_called()
                first = benchmark.refresh(path, "synthetic-key")
                self.assertEqual(len(first["models"]), 3)
                benchmark.refresh(path, "synthetic-key")
                self.assertEqual(fetch.call_count, 1)
                with patch.object(
                    benchmark, "download", side_effect=OSError("private-body-canary")
                ):
                    failed = benchmark.refresh(path, "synthetic-key", force=True)
                self.assertEqual(failed["models"], first["models"])
                self.assertEqual(failed["error"], "benchmark_unavailable")
                self.assertNotIn("private-body-canary", str(failed))
                with patch.object(
                    benchmark, "download", side_effect=benchmark.Quota(100000000000)
                ):
                    limited = benchmark.refresh(path, "synthetic-key", force=True)
                self.assertEqual(limited["error"], "benchmark_rate_limited")
                benchmark.refresh(path, "synthetic-key", force=True)
                self.assertEqual(fetch.call_count, 1)
            self.assertNotIn(
                "synthetic-key", "".join(p.read_text() for p in path.iterdir())
            )


if __name__ == "__main__":
    unittest.main()
