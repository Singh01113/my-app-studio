"""Real MiniLM inference with fixed ONNX weights and a bounded CPU session."""

from pathlib import Path
import os
import hashlib
import threading

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_FILE = "onnx/model_quint8_avx2.onnx"
MODEL_HASHES = {
    "model.onnx": "b941bf19f1f1283680f449fa6a7336bb5600bdcd5f84d10ddc5cd72218a0fd21",
    "tokenizer.json": (
        "be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037"
    ),
}


class Embedder:
    """Masked mean pooling, L2 normalization; one inference at a time."""

    def __init__(self, directory=None):
        directory = Path(
            directory or os.getenv("RAG_MODEL_DIR", "runtime/models/minilm")
        )
        if not (directory / "model.onnx").is_file():
            raise ValueError("Embedding model unavailable. Run scripts/setup_model.py.")
        for name, expected in MODEL_HASHES.items():
            with (directory / name).open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                    raise ValueError("Embedding artifact checksum mismatch.")
        self.tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        self.tokenizer.no_padding()
        self.tokenizer.no_truncation()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(directory / "model.onnx"), options, providers=["CPUExecutionProvider"]
        )
        self.lock = threading.Lock()

    def chunks(self, sections, size=200, overlap=30):
        """Use tokenizer character offsets; preserve original source text."""
        for section in sections:
            text = section["text"]
            offsets = self.tokenizer.encode(text, add_special_tokens=False).offsets
            for start in range(0, len(offsets), size - overlap):
                end = min(start + size, len(offsets))
                content = text[offsets[start][0] : offsets[end - 1][1]]
                yield {
                    "heading": section["heading"],
                    "text": content,
                    "token_count": end - start,
                }
                if end == len(offsets):
                    break

    def encode(self, text):
        """Return a normalized 384-dimensional float32 embedding."""
        encoded = self.tokenizer.encode(text)
        if len(encoded.ids) > 256:
            raise ValueError("Embedding input exceeds 256 tokens.")
        inputs = {
            "input_ids": np.array([encoded.ids], dtype=np.int64),
            "attention_mask": np.array([encoded.attention_mask], dtype=np.int64),
            "token_type_ids": np.array([encoded.type_ids], dtype=np.int64),
        }
        with self.lock:
            output = self.session.run(None, inputs)[0]
        mask = inputs["attention_mask"][..., None]
        pooled = (output * mask).sum(axis=1) / mask.sum(axis=1)
        vector = pooled[0] / max(float(np.linalg.norm(pooled[0])), 1e-12)
        return vector.astype(np.float32).tobytes()
