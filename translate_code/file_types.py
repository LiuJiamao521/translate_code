"""Map file suffixes to comment-parsing strategy."""

from __future__ import annotations

from pathlib import Path

# Python: tokenize.COMMENT; fallback to hash-style if no Python comments found.
PYTHON_SUFFIXES = frozenset({".py", ".pyw", ".pyi"})

# `#` outside "..." / '...' (same heuristic as R): shell, R, Julia, many configs.
HASH_SUFFIXES = frozenset(
    {
        ".r",
        ".sh",
        ".bash",
        ".zsh",
        ".ksh",
        ".csh",
        ".tcsh",
        ".jl",
        ".ps1",
        ".yaml",
        ".yml",
        ".toml",
        ".cmake",
        ".mk",
        ".pl",
        ".pm",
        ".rb",
    }
)


def is_notebook(path: Path) -> bool:
    return path.suffix.lower() == ".ipynb"


def source_comment_kind(path: Path) -> str | None:
    """Return ``python`` | ``hash`` for a non-ipynb file, or ``None`` if unsupported."""
    suf = path.suffix.lower()
    if suf in PYTHON_SUFFIXES:
        return "python"
    if suf in HASH_SUFFIXES:
        return "hash"
    return None


def supported_source_suffixes() -> str:
    """Human-readable list for error messages."""
    exts = sorted(PYTHON_SUFFIXES | HASH_SUFFIXES)
    return ", ".join(exts)
