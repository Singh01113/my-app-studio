"""Download pinned public embedding artifacts; no model credentials required."""

import hashlib
from pathlib import Path
import sys

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.knowledge.embedding import (
    MODEL_FILE,
    MODEL_ID,
    MODEL_REVISION,
)  # pylint: disable=wrong-import-position


def main():
    """Write completed downloads atomically and print public artifact checksums."""
    directory = Path("runtime/models/minilm")
    directory.mkdir(parents=True, exist_ok=True)
    for remote, name in [
        (MODEL_FILE, "model.onnx"),
        ("tokenizer.json", "tokenizer.json"),
    ]:
        url = f"https://huggingface.co/{MODEL_ID}/resolve/{MODEL_REVISION}/{remote}"
        path = directory / name
        if not path.exists():
            with httpx.stream(
                "GET", url, follow_redirects=True, timeout=120
            ) as response:
                response.raise_for_status()
                temporary = path.with_suffix(".download")
                with temporary.open("wb") as stream:
                    for part in response.iter_bytes():
                        stream.write(part)
                temporary.replace(path)
        print(name, hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
