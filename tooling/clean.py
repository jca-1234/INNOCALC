from __future__ import annotations

import os
import shutil
from pathlib import Path

PROTECTED = {".git", ".venv", "artifacts", "reference", "data", "assets", "node_modules"}


def clean(root: Path, *, apply: bool = False) -> list[str]:
    root = root.resolve()
    candidates: list[Path] = []
    for current, directories, _files in os.walk(root, followlinks=False):
        parent = Path(current)
        for name in list(directories):
            path = parent / name
            if name.casefold() in PROTECTED or path.is_symlink() or not path.resolve().is_relative_to(root):
                directories.remove(name)
                continue
            generated = (name == "__pycache__" or name.endswith(".egg-info")
                         or (name in {"build", "dist"} and (parent / "pyproject.toml").is_file()))
            if generated:
                directories.remove(name)
                candidates.append(path)
    if apply:
        for path in candidates:
            shutil.rmtree(path)
    return [path.relative_to(root).as_posix() for path in sorted(candidates)]