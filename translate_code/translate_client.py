from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Callable

import httpx

SYSTEM_PROMPT = (
    "You translate source code comments, docstrings, and string literals from Chinese to concise English. "
    "Preserve identifiers, file paths, package names, numbers, and symbols. "
    "Output must be a JSON array of strings, same length and order as the input array. "
    "Each element is the English translation only, no extra keys or markdown."
)

# Default Chat Completions-compatible JSON endpoint; override with AI_BASE_URL.
DEFAULT_CHAT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


def default_cache_dir() -> Path:
    """Directory next to the installed ``translate_code`` package (editable or site-packages)."""
    return Path(__file__).resolve().parent / "cache"


CACHE_DIR = default_cache_dir()
CACHE_FILE = CACHE_DIR / "cache.json"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_cache(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(path: Path, cache: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")


def _parse_json_array(content: str) -> list[str]:
    text = content.strip()
    fence = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text)
    if fence:
        text = fence.group(1).strip()
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("Model did not return a JSON array")
    return [str(x) for x in data]


def translate_with_chat_api(
    texts: list[str],
    *,
    api_key: str,
    base_url: str = DEFAULT_CHAT_BASE_URL,
    model: str = DEFAULT_MODEL,
    timeout: float = 120.0,
) -> list[str]:
    if not texts:
        return []
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(texts, ensure_ascii=False),
            },
        ],
        "temperature": 0.2,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        body = r.json()
    content = body["choices"][0]["message"]["content"]
    out = _parse_json_array(content)
    if len(out) != len(texts):
        raise ValueError(f"Expected {len(texts)} translations, got {len(out)}")
    return out


def translate_with_cache(
    texts: list[str],
    *,
    api_key: str,
    base_url: str,
    model: str,
    use_cache: bool,
    cache_path: Path | None = None,
    log: Callable[[str], None] | None = None,
) -> list[str]:
    path = cache_path or CACHE_FILE
    cache = _load_cache(path) if use_cache else {}
    results: list[str | None] = [None] * len(texts)
    pending_idx: list[int] = []
    pending_texts: list[str] = []

    for i, t in enumerate(texts):
        key = _sha256(t)
        if use_cache and key in cache:
            results[i] = cache[key]
        else:
            pending_idx.append(i)
            pending_texts.append(t)

    if pending_texts:
        if log:
            log(f"Translating {len(pending_texts)} strings via AI...")
        translated = translate_with_chat_api(
            pending_texts, api_key=api_key, base_url=base_url, model=model
        )
        for j, idx in enumerate(pending_idx):
            val = translated[j]
            results[idx] = val
            if use_cache:
                cache[_sha256(texts[idx])] = val
        if use_cache:
            _save_cache(path, cache)

    return [r if r is not None else "" for r in results]


def mock_translate(texts: list[str]) -> list[str]:
    return [f"[EN] {t.strip()}" if t.strip() else "" for t in texts]


def resolve_model(explicit: str | None) -> str:
    return (explicit or os.environ.get("AI_MODEL") or DEFAULT_MODEL).strip()
