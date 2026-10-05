"""Helpers generated tools may import. Tools with the `files` capability get file access only
through `output_path`, which confines every path to the output directory."""
import os
from pathlib import Path

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs")).resolve()


def output_path(filename: str) -> Path:
    """Path for `filename` inside the output directory; directory parts are stripped."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = (OUTPUT_DIR / Path(filename).name).resolve()
    if path.parent != OUTPUT_DIR:
        raise ValueError("Path escapes output dir")
    return path
