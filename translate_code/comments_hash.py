"""`#` line comments outside quoted strings (R, shell, Julia, YAML, etc.)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HashCommentSpan:
    line_index: int
    hash_col: int
    body: str


def _has_cjk(s: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in s)


def _line_core_and_sep(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    if line.endswith("\r"):
        return line[:-1], "\r"
    return line, ""


def _find_hash_outside_strings(line: str) -> int | None:
    """Index of first `#` that starts a comment (not inside single/double-quoted strings)."""
    i = 0
    n = len(line)
    in_dquote = False
    in_squote = False
    escape = False
    while i < n:
        ch = line[i]
        if escape:
            escape = False
            i += 1
            continue
        if in_dquote:
            if ch == "\\":
                escape = True
            elif ch == '"':
                in_dquote = False
            i += 1
            continue
        if in_squote:
            if ch == "\\":
                escape = True
            elif ch == "'":
                in_squote = False
            i += 1
            continue
        if ch == '"':
            in_dquote = True
            i += 1
            continue
        if ch == "'":
            in_squote = True
            i += 1
            continue
        if ch == "#":
            return i
        i += 1
    return None


def extract_hash_comments(source: str) -> list[HashCommentSpan]:
    spans: list[HashCommentSpan] = []
    lines = source.splitlines(keepends=True)
    for li, line in enumerate(lines):
        core, _sep = _line_core_and_sep(line)
        h = _find_hash_outside_strings(core)
        if h is None:
            continue
        body = core[h + 1 :]
        if not _has_cjk(body):
            continue
        spans.append(HashCommentSpan(li, h, body))
    return spans


def apply_hash_replacements(source: str, updates: list[tuple[HashCommentSpan, str]]) -> str:
    if not updates:
        return source
    lines = source.splitlines(keepends=True)
    for span, translated in sorted(updates, key=lambda x: (x[0].line_index, x[0].hash_col), reverse=True):
        li = span.line_index
        if li < 0 or li >= len(lines):
            continue
        line = lines[li]
        core, sep = _line_core_and_sep(line)
        if span.hash_col >= len(core) or core[span.hash_col] != "#":
            continue
        t = translated.strip()
        new_core = core[: span.hash_col + 1] + (" " + t if t else "")
        lines[li] = new_core + sep
    return "".join(lines)
