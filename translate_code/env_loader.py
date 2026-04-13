"""Load AI settings from optional local files (never commit real secrets)."""

from __future__ import annotations

import os
import re
from pathlib import Path

ENV_FILE_NAME = ".translate-code.env"
SKIP_ENV_VAR = "TRANSLATE_CODE_SKIP_LOCAL_ENV"


def _strip_quotes(val: str) -> str:
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
        return val[1:-1]
    return val


def _parse_line(line: str) -> tuple[str, str] | None:
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    if s.lower().startswith("export "):
        s = s[7:].lstrip()
    if "=" not in s:
        return None
    key, _, raw_val = s.partition("=")
    key = key.strip()
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
        return None
    return key, _strip_quotes(raw_val)


def _apply_env_file(path: Path, *, override: bool) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        pair = _parse_line(line)
        if pair is None:
            continue
        k, v = pair
        if override:
            os.environ[k] = v
        else:
            os.environ.setdefault(k, v)


def _find_env_upward(start: Path) -> Path | None:
    cur = start.resolve()
    for _ in range(512):
        candidate = cur / ENV_FILE_NAME
        if candidate.is_file():
            return candidate
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return None


def load_local_env(*, input_file: Path | None = None) -> None:
    """
    Load environment variables from local files (no network, no extra deps).

    1. ``~/.translate-code.env`` — fills only **missing** keys (``setdefault``).
    2. First ``.translate-code.env`` walking **up** from ``cwd``.
    3. First ``.translate-code.env`` walking **up** from ``input_file``'s directory
       (if not the same file as step 2).

    Steps 2–3 **set** keys from the file (override existing). The file nearest the
    **input path** is applied last, so it wins over the cwd-based file for the same key.
    Step 1 does not replace variables already exported in the shell.
    """
    if os.environ.get(SKIP_ENV_VAR, "").strip().lower() in ("1", "true", "yes"):
        return

    home_file = Path.home() / ENV_FILE_NAME
    _apply_env_file(home_file, override=False)

    applied: set[str] = set()
    starts: list[Path] = [Path.cwd()]
    if input_file is not None:
        starts.append(input_file.parent)

    for start in starts:
        found = _find_env_upward(start)
        if found is None:
            continue
        key = str(found.resolve())
        if key in applied:
            continue
        _apply_env_file(found, override=True)
        applied.add(key)
