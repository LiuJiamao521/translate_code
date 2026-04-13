from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import nbformat


def read_notebook(path: Path) -> nbformat.NotebookNode:
    return nbformat.read(path, as_version=nbformat.NO_CONVERT)


def write_notebook(nb: nbformat.NotebookNode, path: Path) -> None:
    nbformat.write(nb, path)


def cell_source(cell: dict[str, Any]) -> str:
    s = cell.get("source", "")
    if isinstance(s, list):
        return "".join(s)
    return s if isinstance(s, str) else ""


def set_cell_source(cell: dict[str, Any], src: str) -> None:
    cell["source"] = src


def detect_language(cell: dict[str, Any]) -> str:
    meta = cell.get("metadata") or {}
    vscode = meta.get("vscode") or {}
    vid = vscode.get("languageId")
    if isinstance(vid, str) and vid.strip():
        v = vid.strip().lower()
        if v in ("jupyter", "ipython"):
            return "python"
        return v

    src = cell_source(cell)
    if not src.strip():
        return "python"
    first_line = src.lstrip().splitlines()[0] if src.lstrip() else ""
    if first_line.startswith("%%") or first_line.startswith("%"):
        return "python"
    if re.search(r"^\s*(def|import|from|class)\s+\w", src, re.MULTILINE):
        return "python"
    if re.search(r"^\s*(library|require)\s*\(", src, re.MULTILINE):
        return "r"
    return "r"


def _has_cjk(s: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in s)
