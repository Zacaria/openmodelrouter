"""User-keyed benchmark metadata. Never send model lists or conversation data."""

import bisect
import http.client
import json
import math
import os
import re
import tempfile
import time
import ssl
import socket
import threading
from email.utils import parsedate_to_datetime
from pathlib import Path

SECRET = "benchmark-artificial-analysis"
HOST = "artificialanalysis.ai"
ENDPOINT = "/api/v2/language/models/free"
MAX_BYTES = 4 * 1024 * 1024
TIMEOUT = 8
CACHE_SECONDS = 24 * 60 * 60


class Quota(Exception):
    def __init__(self, retry_at):
        self.retry_at = retry_at


def parse(payload, require_scores=True):
    if not isinstance(payload, dict):
        raise ValueError("benchmark_invalid")
    pagination = payload.get("pagination")
    if pagination is not None and (
        not isinstance(pagination, dict)
        or pagination.get("page") != 1
        or pagination.get("total_pages") != 1
        or pagination.get("has_more") is not False
    ):
        raise ValueError("benchmark_invalid")
    version = payload.get("intelligence_index_version")
    if (
        type(version) not in (str, int, float)
        or not str(version)
        or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", str(version))
        or len(str(version)) > 32
        or payload.get("has_more")
        or payload.get("next_cursor")
        or payload.get("next")
    ):
        raise ValueError("benchmark_invalid")
    data = payload.get("data")
    if not isinstance(data, list) or not 1 <= len(data) <= 10000:
        raise ValueError("benchmark_invalid")
    models, seen = [], set()
    for row in data:
        if not isinstance(row, dict):
            raise ValueError("benchmark_invalid")
        slug, name = row.get("slug"), row.get("name")
        if (
            not isinstance(slug, str)
            or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,256}", slug)
            or slug in seen
            or not isinstance(name, str)
            or not 1 <= len(name) <= 256
        ):
            raise ValueError("benchmark_invalid")
        seen.add(slug)
        evaluations = row.get("evaluations") or {}
        if not isinstance(evaluations, dict):
            raise ValueError("benchmark_invalid")
        score = evaluations.get("artificial_analysis_intelligence_index")
        if score is not None and (
            type(score) not in (int, float)
            or not math.isfinite(score)
            or not -100 <= score <= 100
        ):
            raise ValueError("benchmark_invalid")
        models.append({"slug": slug, "name": name, "score": score})
    scores = sorted(m["score"] for m in models if m["score"] is not None)
    if require_scores and not scores:
        raise ValueError("benchmark_invalid")
    for model in models:
        score = model["score"]
        model["quality"] = (
            0
            if score is None
            else 1
            + min(
                2,
                (
                    3
                    * (
                        bisect.bisect_left(scores, score)
                        + bisect.bisect_right(scores, score)
                    )
                )
                // (2 * len(scores)),
            )
        )
    return {"version": str(version), "models": models}


def download(key, context=None):
    # ponytail: shared IPC; bound connected I/O, including trickling headers.
    # DNS still uses the operating system resolver.
    deadline = time.monotonic() + TIMEOUT
    connection = http.client.HTTPSConnection(
        HOST, timeout=TIMEOUT, context=context or ssl.create_default_context()
    )
    response = None

    def expire():
        sock = connection.sock or getattr(
            getattr(getattr(response, "fp", None), "raw", None), "_sock", None
        )
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    timer = threading.Timer(TIMEOUT, expire)
    timer.daemon = True
    timer.start()
    try:
        first, records, size = None, [], 0
        for page in range(1, 101):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError()
            connection.timeout = remaining
            if connection.sock:
                connection.sock.settimeout(remaining)
            path = ENDPOINT + (f"?page={page}" if page > 1 else "")
            connection.request(
                "GET", path, headers={"x-api-key": key, "Accept": "application/json"}
            )
            response = connection.getresponse()
            retry_at = 0
            if response.status == 429 or response.getheader("X-RateLimit-Remaining") == "0":
                reset = response.getheader("X-RateLimit-Reset", "")
                wait = response.getheader("Retry-After", "")
                retry_at = time.time() + 60
                if reset.isdecimal():
                    retry_at = float(reset)
                elif wait.isdecimal():
                    retry_at = time.time() + int(wait)
                elif wait:
                    try:
                        retry_at = parsedate_to_datetime(wait).timestamp()
                    except (TypeError, ValueError, OverflowError):
                        pass
                retry_at = max(time.time() + 1, retry_at)
            if response.status == 429:
                raise Quota(retry_at)
            if response.status in (401, 403):
                raise ValueError("benchmark_access_denied")
            if response.status != 200:
                raise OSError("benchmark_unavailable")
            chunks = []
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError()
                if connection.sock:
                    connection.sock.settimeout(remaining)
                chunk = response.read1(min(65536, MAX_BYTES + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("benchmark_invalid")
            payload = json.loads(b"".join(chunks))
            if not isinstance(payload, dict) or payload.get("tier") not in (
                "free",
                "pro",
                "commercial",
            ):
                raise ValueError("benchmark_invalid")
            pagination = payload.get("pagination")
            rows = payload.get("data")
            if (
                not isinstance(pagination, dict)
                or type(pagination.get("page")) is not int
                or pagination["page"] != page
                or type(pagination.get("total_pages")) is not int
                or not page <= pagination["total_pages"] <= 100
                or type(pagination.get("page_size")) is not int
                or not 1 <= pagination["page_size"] <= 10000
                or pagination.get("has_more") is not (page < pagination["total_pages"])
                or not isinstance(rows, list)
                or not 0 < len(rows) <= pagination["page_size"]
                or (pagination["has_more"] and len(rows) != pagination["page_size"])
            ):
                raise ValueError("benchmark_invalid")
            parse(
                {
                    **payload,
                    "pagination": {
                        "page": 1,
                        "page_size": len(rows),
                        "total_pages": 1,
                        "has_more": False,
                    },
                },
                require_scores=False,
            )
            if first is None:
                first = payload
            elif any(
                payload.get(k) != first.get(k)
                for k in ("tier", "intelligence_index_version")
            ) or any(
                pagination[k] != first["pagination"][k]
                for k in ("total_pages", "page_size")
            ):
                raise ValueError("benchmark_invalid")
            records.extend(rows)
            if len(records) > 10000 or time.monotonic() >= deadline:
                raise ValueError("benchmark_invalid")
            if not pagination["has_more"]:
                return {
                    **first,
                    "_retry_at": retry_at,
                    "data": records,
                    "pagination": {
                        "page": 1,
                        "page_size": len(records),
                        "total_pages": 1,
                        "has_more": False,
                    },
                }
            if retry_at:
                raise Quota(retry_at)
            response.close()
        raise ValueError("benchmark_invalid")
    finally:
        timer.cancel()
        connection.close()


def effective_quality(model, data):
    if model.get("quality_mode") != "benchmark":
        return model["quality"]
    reference = model.get("benchmark_model") or model["upstream"]
    record = data.get(reference)
    return record["quality"] if record and model["quality"] == record["quality"] else 0


def refresh(directory: Path, key, force=False, context=None):
    path = directory / "benchmark-artificial-analysis.json"
    state = {
        "format": 1,
        "version": None,
        "models": [],
        "fetched_at": None,
        "retry_at": 0,
    }
    try:
        if path.stat().st_size <= MAX_BYTES:
            cached = json.loads(path.read_text())
            if cached.get("format") != 1:
                raise ValueError("benchmark_invalid")
            # Re-validate cache scores and tier computation, not arbitrary cached tiers.
            if not cached["models"] and cached["fetched_at"] is None:
                parsed = {"version": None, "models": []}
            else:
                parsed = parse(
                    {
                        "intelligence_index_version": cached["version"],
                        "data": [
                            {
                                "slug": m["slug"],
                                "name": m["name"],
                                "evaluations": {
                                    "artificial_analysis_intelligence_index": m["score"]
                                },
                            }
                            for m in cached["models"]
                        ],
                    }
                )
            fetched_at = cached["fetched_at"]
            retry_at = cached.get("retry_at", 0)
            if (
                (
                    fetched_at is not None
                    and (
                        type(fetched_at) not in (int, float)
                        or not math.isfinite(fetched_at)
                        or fetched_at > time.time() + 60
                    )
                )
                or type(retry_at) not in (int, float)
                or not math.isfinite(retry_at)
            ):
                raise ValueError("benchmark_invalid")
            state.update(parsed, fetched_at=fetched_at, retry_at=retry_at)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        pass
    state.update(configured=bool(key), error=None)
    now = time.time()
    if not key:
        state["error"] = "benchmark_key_required"
        return state
    if state["retry_at"] > now:
        state["error"] = "benchmark_rate_limited"
        return state
    if not force and state["fetched_at"] and now - state["fetched_at"] < CACHE_SECONDS:
        return state
    updated = None
    try:
        downloaded = download(key, context)
        state["retry_at"] = downloaded.get("_retry_at", 0)
        updated = {
            **state,
            **parse(downloaded),
            "fetched_at": time.time(),
            "retry_at": downloaded.get("_retry_at", 0),
        }
    except Quota as error:
        state.update(error="benchmark_rate_limited", retry_at=error.retry_at)
        updated = state
    except (
        OSError,
        http.client.HTTPException,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        RecursionError,
    ) as error:
        state["error"] = (
            "benchmark_access_denied"
            if str(error) == "benchmark_access_denied"
            else "benchmark_unavailable"
        )
        if state["retry_at"] <= time.time():
            return state
        updated = state
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=directory, delete=False) as file:
            temporary = file.name
            json.dump(updated, file, allow_nan=False)
        os.replace(temporary, path)
    except (OSError, ValueError):
        state["error"] = "benchmark_storage_unavailable"
        return state
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    return updated
