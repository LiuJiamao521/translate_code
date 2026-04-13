"""R hash-style comments; same lexer as shell-like `#` comments."""

from __future__ import annotations

from translate_code.comments_hash import (
    HashCommentSpan as RCommentSpan,
    apply_hash_replacements as apply_r_replacements,
    extract_hash_comments as extract_r_comments,
)

__all__ = ["RCommentSpan", "apply_r_replacements", "extract_r_comments"]
