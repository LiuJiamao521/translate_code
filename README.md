# translate-code

CLI tool that translates **Chinese** text in **code comments**, **Python docstrings / string literals**, and optionally **Jupyter markdown cells** to **English**. The parser is chosen from the **file suffix**.

| Kind | Examples | What gets scanned |
|------|----------|-------------------|
| Jupyter | `.ipynb` | Code cells (`#`, `"""`…); optional `--markdown` for CJK in markdown cells |
| Python | `.py`, `.pyw`, `.pyi` | `tokenize` comments + string literals; hash-style `#` fallback |
| R / shell / similar | `.r`, `.sh`, `.bash`, `.zsh`, … | First `#` outside `"` / `'`, to end of line |
| Other `#` languages | `.jl`, `.ps1`, `.yaml`, `.yml`, `.toml`, … | Same hash heuristic |

Notebook **outputs** are not modified. Unknown suffixes print an error and list supported extensions.

---

## Install

**From a clone (editable, for development)**

```bash
git clone https://github.com/YOUR_GITHUB_USER/YOUR_REPO.git
cd YOUR_REPO
python3 -m pip install -e .
```

**From the repo directory without git**

```bash
python3 -m pip install .
```

Dependencies: `nbformat`, `httpx` (also listed in `requirements.txt`).

After install:

```bash
translate-code --help
python3 -m translate_code --help
```

> **Before publishing:** replace `YOUR_GITHUB_USER` / `YOUR_REPO` in [`pyproject.toml`](pyproject.toml) under `[project.urls]` with your real GitHub paths (or remove that section if you prefer).

---

## Quick start

**1. Preview (no write, no AI)**

```bash
translate-code notebook.ipynb --dry-run
translate-code script.py --dry-run
translate-code run.sh --dry-run
```

**2. Offline check (mock translations)**

```bash
translate-code analysis.py --mock -o analysis.mock.py
translate-code pipeline.sh --mock -o pipeline.mock.sh
```

**3. Real translation (AI API)**

Use any **Chat Completions–compatible** HTTPS API (Bearer token, JSON body).

```bash
export AI_API_KEY="your-api-key-here"
export AI_BASE_URL="https://example.com/v1"   # optional; built-in default if unset
export AI_MODEL="your-model-id"                   # optional

translate-code script.r -o script.en.r
translate-code notebook.ipynb -o notebook.en.ipynb --markdown
```

Without `-o`, the input file is overwritten. With `--backup`, a `.bak` copy is written next to the input.

---

## CLI flags

| Flag | Meaning |
|------|---------|
| `-o` / `--output` | Output path |
| `--backup` | Save `.bak` before overwrite |
| `--dry-run` | List translatable strings only |
| `--mock` | `[EN]` prefix, no AI |
| `--markdown` | Translate CJK in markdown cells (`.ipynb` only) |
| `--no-cache` | Disable on-disk cache |
| `--no-local-env` | Do not read `.translate-code.env` files |
| `--model` | Override `AI_MODEL` |
| `--cache-file` | Custom cache JSON (default: `translate_code/cache/cache.json` beside the installed package) |

---

## Environment variables

| Variable | Required for AI | Role |
|----------|-----------------|------|
| `AI_API_KEY` | Yes (unless `--mock`) | Bearer token |
| `AI_BASE_URL` | No | API root |
| `AI_MODEL` | No | Model id |

### Local env file (not for GitHub)

You can store the above in a file instead of exporting them in every shell session.

| File | Purpose |
|------|---------|
| `~/.translate-code.env` | User-wide defaults; only fills variables **not** already set in the shell |
| `.translate-code.env` | Project file: searched upward from **current working directory**, then from **the input file’s directory**; each file **overwrites** `AI_*` keys for that run |

Format is simple `KEY=value` lines (`export KEY=value` is OK). See [`.translate-code.env.example`](.translate-code.env.example).

- Add **`.translate-code.env`** to `.gitignore` (already listed in this repo) — **do not commit** real secrets.
- To disable loading these files: `--no-local-env` or `export TRANSLATE_CODE_SKIP_LOCAL_ENV=1`.

---

## Project layout

```text
translate_code/          # Python package
  cli.py                 # Entry point
  env_loader.py          # Optional .translate-code.env files
  translate_client.py    # HTTP + cache
  comments_*.py          # Comment extraction
  python_literals.py     # Python strings / docstrings
  ipynb_io.py            # Notebook read/write
  file_types.py          # Suffix → parser
  cache/                 # Default cache dir (gitignored JSON)
test.py, test.R, test.ipynb   # Optional local smoke tests (Chinese comments)
```

---

## Notes

- **Cache:** identical Chinese snippets are reused from disk unless `--no-cache`. Default cache lives under the installed `translate_code` package (see `.gitignore`).
- **Edge cases:** complex shell/R quoting or f-strings may be skipped; use `--dry-run` / `--mock` and review diffs on critical files.

---

## License

[MIT](LICENSE)
