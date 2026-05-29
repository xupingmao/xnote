# AGENTS.md — xnote

## Quick start

```sh
# copy local config (required, cannot use defaults directly)
cp config/boot/boot.min.properties boot.local.properties
# start server
python app.py --config boot.local.properties
```

Open http://localhost:1234 ; admin/admin.

## Run tests

```sh
# all tests (updates config/version.txt, cleans testdata/)
python tools/run-test.py

# focused targets (see tools/run-test.py for full list)
python tools/run-test.py app      # handlers
python tools/run-test.py xutils   # xutils lib
python tools/run-test.py note     # note handlers
python tools/run-test.py xutils_db  # kv db layer
python tools/run-test.py xutils_sqldb  # sql db layer

# bypass runner (pytest directly)
python -m pytest tests/test_app.py --doctest-modules --cov xnote_handlers --capture no
```

Test runner always runs `doctest-modules` and `--cov`. It uses `config/boot/boot.test.properties` (data dir = `./testdata/`).

## Architecture

| Layer | Directory | Role |
|-------|-----------|------|
| Entry | `app.py` / `main.py` | Delegates to `xnote.core.xnote_app.main()` |
| Core framework | `xnote/core/` | Routing (webpy fork), config, auth, templates, DB lifecycle |
| HTTP handlers | `xnote_handlers/` | All page & API handlers (note, fs, tools, plugins, system, etc.) |
| Utilities | `xutils/` | DB drivers, file I/O, text parsing, cache, date, etc. |
| Config | `config/boot/` | Properties files; `boot.test.properties` for tests |

## URL routing

Handlers register via a module-level `xurls` tuple:

```python
xurls = (
    r"/path", MyHandler,
)
```

`xmanager` auto-discovers all modules under `xnote_handlers/` reading `xurls`. No central route table.

## Key conventions

- **Properties config**: Custom `.properties` parser (`xutils.text_parser_properties.py`). Types declared as `key.type = bool|int`. Never use the default `config/boot/boot.default.properties` directly (safe-guard in code).
- **Test env**: `tests/test_base.py` calls `xconfig.init()` with `boot.test.properties`, uses SqliteKV, auto-logs-in admin. Define test classes extending `test_base.BaseTestCase`.
- **DB drivers**: sqlite (default), leveldb, lmdb, mysql, ssdb. On Windows leveldb fallback → leveldbpy.
- **Code style**: PEP8 + `docs/code_style.md`. `xurls` tuples, handlers are classes with `GET(self)` / `POST(self)` etc.
- **Version**: `config/version.txt` — auto-updated during test run.
- **Sentinel**: `sentinel.py` wraps the server; exit code 205 or 52480 triggers restart.
- **Build step**: `tools/build.py` builds CSS/JS bundles before production runs.
