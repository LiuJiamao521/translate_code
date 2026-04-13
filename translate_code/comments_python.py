from __future__ import annotations

import io
import tokenize
from dataclasses import dataclass


@dataclass(frozen=True)
class PyCommentSpan:
    """0-based line index; columns are Unicode character offsets on that line."""

    line_index: int
    col_start: int
    col_end: int
    body: str


def _has_cjk(s: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in s)


def extract_python_comments(source: str) -> list[PyCommentSpan]:
    spans: list[PyCommentSpan] = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    except (tokenize.TokenError, SyntaxError):
        return []
    for tok in tokens:
        if tok.type != tokenize.COMMENT:
            continue
        body = tok.string[1:].lstrip()
        if not _has_cjk(body):
            continue
        sl, sc = tok.start
        el, ec = tok.end
        spans.append(PyCommentSpan(sl - 1, sc, ec, body))
    return spans


def apply_python_replacements(source: str, updates: list[tuple[PyCommentSpan, str]]) -> str:
    """Backward-compatible wrapper: comment-only updates via absolute offsets."""
    if not updates:
        return source
    from translate_code.python_literals import apply_python_mixed

    return apply_python_mixed(source, updates, [], [])
