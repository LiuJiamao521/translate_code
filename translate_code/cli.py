from __future__ import annotations

import argparse
import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from translate_code.comments_hash import (
    HashCommentSpan,
    apply_hash_replacements,
    extract_hash_comments,
)
from translate_code.comments_python import (
    PyCommentSpan,
    extract_python_comments,
)
from translate_code.python_literals import (
    PyStringLiteralSpan,
    apply_python_mixed,
    extract_python_string_literals,
)
from translate_code.comments_r import (
    RCommentSpan,
    apply_r_replacements,
    extract_r_comments,
)
from translate_code.env_loader import ENV_FILE_NAME, load_local_env
from translate_code.file_types import (
    is_notebook,
    source_comment_kind,
    supported_source_suffixes,
)
from translate_code.ipynb_io import (
    _has_cjk,
    cell_source,
    detect_language,
    read_notebook,
    set_cell_source,
    write_notebook,
)
from translate_code.translate_client import (
    CACHE_FILE,
    DEFAULT_CHAT_BASE_URL,
    mock_translate,
    resolve_model,
    translate_with_cache,
)


def _lang_processes_comments(lang: str) -> bool:
    return lang.lower() in ("python", "r", "s", "rscript")


def _collect_code_cell_work(src: str, lang: str) -> tuple[list[PyCommentSpan], list[RCommentSpan]]:
    lang_l = lang.lower()
    if lang_l == "python":
        return extract_python_comments(src), []
    if lang_l in ("r", "s", "rscript"):
        return [], extract_r_comments(src)
    return [], []


def _apply_code_cell(
    src: str,
    lang: str,
    py_updates: list[tuple[PyCommentSpan, str]],
    r_updates: list[tuple[RCommentSpan, str]],
    string_updates: list[tuple[PyStringLiteralSpan, str]],
) -> str:
    lang_l = lang.lower()
    if lang_l == "python":
        if py_updates or string_updates:
            return apply_python_mixed(src, py_updates, [], string_updates)
        return src
    if lang_l in ("r", "s", "rscript") and r_updates:
        return apply_r_replacements(src, r_updates)
    return src


def _translate_unique_comments(
    unique_comments: list[str],
    *,
    mock: bool,
    use_cache: bool,
    cache_file: Path | None,
    model: str | None,
    log: Callable[[str], None],
) -> dict[str, str] | None:
    if not unique_comments:
        return {}
    if mock:
        return dict(zip(unique_comments, mock_translate(unique_comments)))
    api_key = os.environ.get("AI_API_KEY", "").strip()
    if not api_key:
        log("Error: AI_API_KEY is not set (or use --mock).")
        return None
    base_url = os.environ.get("AI_BASE_URL", DEFAULT_CHAT_BASE_URL).strip()
    m = resolve_model(model)
    translated = translate_with_cache(
        unique_comments,
        api_key=api_key,
        base_url=base_url,
        model=m,
        use_cache=use_cache,
        cache_path=cache_file,
        log=log,
    )
    return dict(zip(unique_comments, translated))


def run_notebook(
    input_path: Path,
    output_path: Path | None,
    *,
    backup: bool,
    dry_run: bool,
    mock: bool,
    markdown: bool,
    use_cache: bool,
    cache_file: Path | None,
    model: str | None,
) -> int:
    def log(msg: str) -> None:
        print(msg, file=sys.stderr)

    nb = read_notebook(input_path)

    code_jobs: list[
        tuple[
            int,
            str,
            str,
            list[PyCommentSpan],
            list[RCommentSpan],
            list[PyStringLiteralSpan],
        ]
    ] = []
    md_indices: list[int] = []
    md_sources: list[str] = []

    for i, cell in enumerate(nb.cells):
        if cell.get("cell_type") != "code":
            if markdown and cell.get("cell_type") == "markdown":
                msrc = cell_source(cell)
                if _has_cjk(msrc):
                    md_indices.append(i)
                    md_sources.append(msrc)
            continue
        src = cell_source(cell)
        lang = detect_language(cell)
        if not _lang_processes_comments(lang):
            log(f"Warning: cell {i} language {lang!r} is not supported; skipping comments.")
            continue
        py_spans, r_spans = _collect_code_cell_work(src, lang)
        effective_lang = lang
        if lang.lower() == "python" and not py_spans:
            r_try = extract_r_comments(src)
            if r_try:
                r_spans = r_try
                effective_lang = "r"
        string_spans: list[PyStringLiteralSpan] = []
        if effective_lang == "python":
            string_spans = extract_python_string_literals(src)
        if not py_spans and not r_spans and not string_spans:
            continue
        code_jobs.append((i, effective_lang, src, py_spans, r_spans, string_spans))

    comment_bodies: list[str] = []
    for _i, _lang, _src, py_spans, r_spans, string_spans in code_jobs:
        for s in py_spans:
            comment_bodies.append(s.body)
        for s in r_spans:
            comment_bodies.append(s.body)
        for s in string_spans:
            comment_bodies.append(s.decoded)

    unique_comments = list(dict.fromkeys(comment_bodies))

    if dry_run:
        log("Dry run: no file will be written.")
        for b in unique_comments:
            print(b)
        for j, m in enumerate(md_sources):
            log(f"--- markdown cell {md_indices[j]} ---")
            print(m[:500] + ("..." if len(m) > 500 else ""))
        log(f"Total unique translatable strings: {len(unique_comments)}")
        log(f"Markdown cells with CJK: {len(md_sources)}")
        return 0

    translations_map = _translate_unique_comments(
        unique_comments,
        mock=mock,
        use_cache=use_cache,
        cache_file=cache_file,
        model=model,
        log=log,
    )
    if translations_map is None:
        return 1

    md_translations: dict[int, str] = {}
    if md_sources:
        if mock:
            md_out = mock_translate(md_sources)
        else:
            api_key = os.environ.get("AI_API_KEY", "").strip()
            if not api_key:
                log("Error: AI_API_KEY is not set (or use --mock).")
                return 1
            base_url = os.environ.get("AI_BASE_URL", DEFAULT_CHAT_BASE_URL).strip()
            m = resolve_model(model)
            md_out = translate_with_cache(
                md_sources,
                api_key=api_key,
                base_url=base_url,
                model=m,
                use_cache=use_cache,
                cache_path=cache_file,
                log=log,
            )
        md_translations = dict(zip(md_indices, md_out))

    for i, lang, src, py_spans, r_spans, string_spans in code_jobs:
        py_updates: list[tuple[PyCommentSpan, str]] = [
            (s, translations_map[s.body]) for s in py_spans
        ]
        r_updates: list[tuple[RCommentSpan, str]] = [
            (s, translations_map[s.body]) for s in r_spans
        ]
        str_updates: list[tuple[PyStringLiteralSpan, str]] = [
            (sub, translations_map[sub.decoded]) for sub in string_spans
        ]
        new_src = _apply_code_cell(src, lang, py_updates, r_updates, str_updates)
        set_cell_source(nb.cells[i], new_src)

    for idx, text in md_translations.items():
        set_cell_source(nb.cells[idx], text)

    out = output_path or input_path
    if backup and out == input_path:
        bak = input_path.with_suffix(input_path.suffix + ".bak")
        shutil.copy2(input_path, bak)
        log(f"Backup written to {bak}")
    write_notebook(nb, out)
    log(f"Wrote {out}")
    return 0


def run_source_file(
    input_path: Path,
    output_path: Path | None,
    kind: str,
    *,
    backup: bool,
    dry_run: bool,
    mock: bool,
    use_cache: bool,
    cache_file: Path | None,
    model: str | None,
) -> int:
    def log(msg: str) -> None:
        print(msg, file=sys.stderr)

    src = input_path.read_text(encoding="utf-8")
    py_spans: list[PyCommentSpan] = []
    hash_spans: list[HashCommentSpan] = []
    effective = kind
    if kind == "python":
        py_spans = extract_python_comments(src)
        if not py_spans:
            hash_spans = extract_hash_comments(src)
            if hash_spans:
                effective = "hash"
    else:
        hash_spans = extract_hash_comments(src)

    string_spans = extract_python_string_literals(src) if kind == "python" else []
    bodies: list[str] = (
        [s.body for s in py_spans]
        + [s.body for s in hash_spans]
        + [s.decoded for s in string_spans]
    )
    unique_comments = list(dict.fromkeys(bodies))

    if dry_run:
        log("Dry run: no file will be written.")
        for b in unique_comments:
            print(b)
        log(f"Total unique translatable strings: {len(unique_comments)}")
        return 0

    if not unique_comments:
        log("No Chinese in comments or string literals; not writing.")
        return 0

    translations_map = _translate_unique_comments(
        unique_comments,
        mock=mock,
        use_cache=use_cache,
        cache_file=cache_file,
        model=model,
        log=log,
    )
    if translations_map is None:
        return 1

    str_updates = [(s, translations_map[s.decoded]) for s in string_spans]
    if kind == "python":
        py_updates = (
            [(s, translations_map[s.body]) for s in py_spans] if effective == "python" and py_spans else []
        )
        hash_updates = [(s, translations_map[s.body]) for s in hash_spans] if hash_spans else []
        if py_updates or hash_updates or str_updates:
            new_src = apply_python_mixed(src, py_updates, hash_updates, str_updates)
        else:
            new_src = src
    elif hash_spans:
        h_updates = [(s, translations_map[s.body]) for s in hash_spans]
        new_src = apply_hash_replacements(src, h_updates)
    else:
        new_src = src

    out = output_path or input_path
    if backup and out == input_path:
        bak = input_path.with_suffix(input_path.suffix + ".bak")
        shutil.copy2(input_path, bak)
        log(f"Backup written to {bak}")
    out.write_text(new_src, encoding="utf-8")
    log(f"Wrote {out}")
    return 0


def run(
    input_path: Path,
    output_path: Path | None,
    *,
    backup: bool,
    dry_run: bool,
    mock: bool,
    markdown: bool,
    use_cache: bool,
    cache_file: Path | None,
    model: str | None,
) -> int:
    def log(msg: str) -> None:
        print(msg, file=sys.stderr)

    if is_notebook(input_path):
        return run_notebook(
            input_path,
            output_path,
            backup=backup,
            dry_run=dry_run,
            mock=mock,
            markdown=markdown,
            use_cache=use_cache,
            cache_file=cache_file,
            model=model,
        )

    skind = source_comment_kind(input_path)
    if skind is None:
        print(
            f"Error: unsupported file type {input_path.suffix!r}. "
            f"Use .ipynb or one of: {supported_source_suffixes()}",
            file=sys.stderr,
        )
        return 1

    if markdown:
        log("Note: --markdown applies to .ipynb only; ignored for this file.")

    return run_source_file(
        input_path,
        output_path,
        skind,
        backup=backup,
        dry_run=dry_run,
        mock=mock,
        use_cache=use_cache,
        cache_file=cache_file,
        model=model,
    )


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Translate Chinese in code comments, Python docstrings, and other string literals "
            "for notebooks (.ipynb) or scripts (.py, .r, .sh, ...); rules follow the file suffix."
        )
    )
    p.add_argument(
        "input",
        type=Path,
        help="Input .ipynb, .py, .r, .sh, or other supported file",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input)",
    )
    p.add_argument(
        "--backup",
        action="store_true",
        help="Write a .bak copy next to the input before overwriting",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print translatable strings only; no AI call and no write",
    )
    p.add_argument(
        "--mock",
        action="store_true",
        help="Prefix comments with [EN] instead of calling the AI API",
    )
    p.add_argument(
        "--markdown",
        action="store_true",
        help="Also translate markdown cells that contain CJK (.ipynb only)",
    )
    p.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable on-disk translation cache",
    )
    p.add_argument(
        "--model",
        default=None,
        help="Model name (default: AI_MODEL env or built-in default)",
    )
    p.add_argument(
        "--cache-file",
        type=Path,
        default=None,
        help=f"Translation cache JSON (default: {CACHE_FILE})",
    )
    p.add_argument(
        "--no-local-env",
        action="store_true",
        help=(
            f"Skip loading {ENV_FILE_NAME} from home or parent directories of the input file / cwd "
            f"(or set environment variable TRANSLATE_CODE_SKIP_LOCAL_ENV=1)."
        ),
    )
    args = p.parse_args()
    input_path = args.input.resolve()
    if not input_path.is_file():
        print(f"Error: not a file: {input_path}", file=sys.stderr)
        sys.exit(1)
    if not args.no_local_env:
        load_local_env(input_file=input_path)
    output_path = args.output.resolve() if args.output else None
    if args.dry_run:
        out_for_run = None
    else:
        out_for_run = output_path or input_path

    rc = run(
        input_path,
        out_for_run,
        backup=args.backup,
        dry_run=args.dry_run,
        mock=args.mock,
        markdown=args.markdown,
        use_cache=not args.no_cache,
        cache_file=args.cache_file,
        model=args.model,
    )
    sys.exit(rc)


if __name__ == "__main__":
    main()
