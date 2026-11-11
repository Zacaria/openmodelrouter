"""Load the s1d1 router and decode its 21 outputs, with a PyTorch, MLX or ONNX Runtime backend. Python >= 3.10.

    from s1d1_router import Router
    router = Router("scombat/s1d1-router", device="mps")      # a Hub repo id or a local folder; device cpu, mps or cuda
    router.route(["Quelle est la capitale de l'Australie ?"])

Output 0 is the complexity in tier units (score = 0.5 + 0.25 * output, clipped to 0.01 .. 1.00), outputs 1..19
are the task logits (TASKS), output 20 is the needs_tools logit. Every backend returns the raw 21 logits.
A Hub repo id is first resolved to a local folder (`snapshot_download`, weights and json files only); the backend is
then read from variant.json in that folder (PyTorch when absent), so the MLX and ONNX variants load from the Hub too.
Tokenization uses the `tokenizers` library alone (tokenizer.json). The MLX backend needs `mlx-embeddings`, the ONNX
backend `onnxruntime`; PyTorch and transformers are imported only for the torch backend.
"""
import json
import os

import numpy as np
from tokenizers import Tokenizer

TASKS = (
    "information_seeking", "reasoning", "planning", "editing", "summarization", "extraction",
    "classification", "translation", "coding_debugging", "math", "data_analysis", "writing",
    "role_playing", "advice_seeking", "brainstorming", "completion", "action_execution", "chat", "other",
)
# Tiers reported by decode(): the nearest anchor. The judge's scale had a fifth anchor, `expert` at 1.00, too rare to
# learn (3 test rows, never predicted), so scores above 0.875 are reported as `high`; the score itself goes up to 1.00.
TIERS = (("trivial", 0.01), ("low", 0.25), ("medium", 0.50), ("high", 0.75))
MAX_LENGTH = 1024  # the length the router was trained with
COMPLEXITY_CENTER, COMPLEXITY_SCALE = 0.5, 0.25
VOCAB_MAP = "vocab_map.npy"  # old token id -> new token id, written by `07_variants.py prune` for a pruned vocabulary
MARKER = "variant.json"  # written next to the weights by pipeline/07_variants.py: {"backend": "torch" | "mlx" | "onnx", ...}
HUB_FILES = ("*.json", "*.safetensors", "*.onnx", "*.npy")  # what a backend needs from a Hub repo


def local_folder(repo: str) -> str:
    """`repo` itself when it is a folder, else the local snapshot of that Hub repo (downloaded once, then cached)."""
    if os.path.isdir(repo):
        return repo
    from huggingface_hub import snapshot_download

    return snapshot_download(repo, allow_patterns=list(HUB_FILES))


def backend_of(folder: str) -> str:
    path = os.path.join(folder, MARKER)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)["backend"]
    return "torch"


def decode(logits: np.ndarray, tokens: np.ndarray) -> list[dict]:
    results = []
    for row, n in zip(logits.astype(np.float32), tokens, strict=True):
        score = float(np.clip(COMPLEXITY_CENTER + COMPLEXITY_SCALE * row[0], 0.01, 1.0))
        p_tools = float(1 / (1 + np.exp(-row[-1])))
        results.append({
            "complexity_score": round(score, 3),
            "complexity_tier": min(TIERS, key=lambda t: abs(t[1] - score))[0],
            "task": TASKS[int(row[1:1 + len(TASKS)].argmax())],
            "needs_tools_probability": round(p_tools, 3),
            "needs_tools": p_tools >= 0.5,
            "prompt_tokens": int(n),
        })
    return results


def load_tokenizer(folder: str) -> Tokenizer:
    """tokenizer.json of a local folder, truncating at MAX_LENGTH and padding to the longest prompt."""
    tokenizer = Tokenizer.from_file(os.path.join(folder, "tokenizer.json"))
    with open(os.path.join(folder, "tokenizer_config.json"), encoding="utf-8") as f:
        pad = json.load(f).get("pad_token", "<pad>")
    tokenizer.enable_truncation(MAX_LENGTH)
    tokenizer.enable_padding(pad_id=tokenizer.token_to_id(pad), pad_token=pad)
    return tokenizer


class Router:
    def __init__(self, repo: str, device: str = "cpu", backend: str = "auto"):
        """`repo`: Hub repo id or local folder. `device` (torch backend only): cpu, mps or cuda; the published latency is
        on mps. `backend`: auto (from variant.json), torch, mlx or onnx."""
        folder = local_folder(repo)
        self.backend = backend_of(folder) if backend == "auto" else backend
        self.tokenizer = load_tokenizer(folder)
        map_path = os.path.join(folder, VOCAB_MAP)
        self.vocab_map = np.load(map_path) if os.path.isfile(map_path) else None
        if self.backend == "torch":
            import torch
            from transformers import AutoModelForSequenceClassification

            self._torch = torch
            self.device = device
            dtype = torch.float32 if device == "cpu" else "auto"  # fp16 on a CPU is slow in PyTorch
            self.model = AutoModelForSequenceClassification.from_pretrained(folder, dtype=dtype).to(device).eval()
        elif self.backend == "mlx":
            from mlx_embeddings.utils import load_model
            from pathlib import Path

            self.model = load_model(Path(folder))
        elif self.backend == "onnx":
            import onnxruntime

            with open(os.path.join(folder, MARKER), encoding="utf-8") as f:
                name = json.load(f).get("file", "model.onnx")
            self.session = onnxruntime.InferenceSession(os.path.join(folder, name), providers=["CPUExecutionProvider"])
        else:
            raise ValueError(f"unknown backend {self.backend!r}")

    def logits(self, prompts: list[str]) -> tuple[np.ndarray, np.ndarray]:
        """Raw 21 logits of each prompt and its token count."""
        encoded = self.tokenizer.encode_batch(prompts)
        ids = np.array([e.ids for e in encoded], dtype=np.int64)
        mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
        return self._forward(ids, mask), mask.sum(1)

    def logits_from_ids(self, sequences: list[list[int]]) -> tuple[np.ndarray, np.ndarray]:
        """Raw 21 logits of token-id sequences that already hold their special tokens (`logits` without the tokenizer:
        for pieces cut from a long prompt). Right-padded to the longest sequence, at most MAX_LENGTH tokens each."""
        if any(len(s) > MAX_LENGTH for s in sequences):
            raise ValueError(f"a sequence is longer than {MAX_LENGTH} tokens")
        pad = self.tokenizer.padding["pad_id"]
        width = max(len(s) for s in sequences)
        ids = np.array([s + [pad] * (width - len(s)) for s in sequences], dtype=np.int64)
        mask = np.array([[1] * len(s) + [0] * (width - len(s)) for s in sequences], dtype=np.int64)
        return self._forward(ids, mask), mask.sum(1)

    def _forward(self, ids: np.ndarray, mask: np.ndarray) -> np.ndarray:
        if self.vocab_map is not None:
            ids = self.vocab_map[ids]
        if self.backend == "torch":
            with self._torch.no_grad():
                out = self.model(input_ids=self._torch.from_numpy(ids).to(self.device),
                                 attention_mask=self._torch.from_numpy(mask).to(self.device)).logits
            logits = out.float().cpu().numpy()
        elif self.backend == "mlx":
            import mlx.core as mx
            from mlx_embeddings.models.modernbert import mean_pooling

            m = self.model
            hidden = m.model(mx.array(ids), attention_mask=mx.array(mask), position_ids=None,
                             output_hidden_states=None, return_dict=False)[0]
            # the library's own forward applies a softmax to the logits: take the pieces and stop before it
            out = m.classifier(m.head(mean_pooling(hidden, mx.array(mask))))
            logits = np.array(out.astype(mx.float32))
        else:
            logits = self.session.run(None, {"input_ids": ids.astype(np.int64), "attention_mask": mask.astype(np.int64)})[0]
        return logits

    def route(self, prompts: list[str]) -> list[dict]:
        logits, tokens = self.logits(prompts)
        return decode(logits, tokens)
