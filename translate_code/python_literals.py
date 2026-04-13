"""Detect CJK inside Python string tokens (docstrings and other string literals)."""

from __future__ import annotations

import ast
import io
import tokenize
from dataclasses import dataclass

from translate_code.comments_hash import HashCommentSpan, _line_core_and_sep
from translate_code.comments_python import PyCommentSpan


def _has_cjk(s: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in s)


@dataclass(frozen=True)
class PyStringLiteralSpan:
    """Absolute character offsets in the full source (matches ``tokenize`` positions)."""

    abs_start: int
    abs_end: int
    decoded: str


def _abs_pos_from_token(lines: list[str], start: tuple[int, int]) -> int:
    line_no, col = start
    return sum(len(lines[i]) for i in range(line_no - 1)) + col


def extract_python_string_literals(source: str) -> list[PyStringLiteralSpan]:
    """
    String tokens where ``ast.literal_eval`` yields a ``str`` containing CJK.
    Skips f-strings and other literals that cannot be parsed with ``literal_eval``.
    """
    lines = source.splitlines(keepends=True)
    spans: list[PyStringLiteralSpan] = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    except (tokenize.TokenError, SyntaxError):
        return []
    for tok in tokens:
        if tok.type != tokenize.STRING:
            continue
        raw = tok.string
        try:
            decoded = ast.literal_eval(raw)
        except (ValueError, SyntaxError, MemoryError, TypeError):
            continue
        if not isinstance(decoded, str) or not _has_cjk(decoded):
            continue
        abs_s = _abs_pos_from_token(lines, tok.start)
        abs_e = _abs_pos_from_token(lines, tok.end)
        if source[abs_s:abs_e] != raw:
            continue
        spans.append(PyStringLiteralSpan(abs_s, abs_e, decoded))
    return spans


def encode_python_string_value(value: str) -> str:
    """Serialize a Python ``str`` so multi-line text stays as a triple-quoted literal (docstring-friendly)."""
    if "\n" in value:
        inner = value.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
        return '"""' + inner + '"""'
    return ast.unparse(ast.Constant(value=value))


def apply_abs_replacements(source: str, repls: list[tuple[int, int, str]]) -> str:
    for a, b, text in sorted(repls, key=lambda x: x[0], reverse=True):
        source = source[:a] + text + source[b:]
    return source


def _py_comment_abs(lines: list[str], span: PyCommentSpan) -> tuple[int, int]:
    base = sum(len(lines[i]) for i in range(span.line_index))
    return base + span.col_start, base + span.col_end


def _hash_comment_abs(lines: list[str], span: HashCommentSpan) -> tuple[int, int]:
    base = sum(len(lines[i]) for i in range(span.line_index))
    line = lines[span.line_index]
    core, _ = _line_core_and_sep(line)
    if span.hash_col >= len(core) or core[span.hash_col] != "#":
        return base, base
    a = base + span.hash_col
    b = base + len(core)
    return a, b


def apply_python_mixed(
    source: str,
    py_comments: list[tuple[PyCommentSpan, str]],
    hash_comments: list[tuple[HashCommentSpan, str]],
    string_literals: list[tuple[PyStringLiteralSpan, str]],
) -> str:
    """
    Apply `#` comments (token or hash lexer) and string literal replacements using
    absolute offsets so multi-line ``\"\"\"`` blocks are handled correctly.
    """
    if not py_comments and not hash_comments and not string_literals:
        return source
    lines = source.splitlines(keepends=True)
    repls: list[tuple[int, int, str]] = []
    for span, t in string_literals:
        repls.append((span.abs_start, span.abs_end, encode_python_string_value(t)))
    for span, t in py_comments:
        a, b = _py_comment_abs(lines, span)
        ts = t.strip()
        repls.append((a, b, "#" + (" " + ts if ts else "")))
    for span, t in hash_comments:
        a, b = _hash_comment_abs(lines, span)
        if a == b:
            continue
        ts = t.strip()
        repls.append((a, b, "#" + (" " + ts if ts else "")))
    return apply_abs_replacements(source, repls)
