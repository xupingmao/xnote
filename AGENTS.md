# AGENTS.md — xnote

## 编程规范

- 简单原则：如果满足需求目标有多个方案，优先选择简单的方案
- 职责单一原则：一个方法不要做多件事情
- 分层原则：按照view/biz/dao三层分层，简单场景可以直接view/dao两层
- 可自动化：开发完一个功能后，需要补充对应的自动化测试脚本并且测试通过

## Quick start

```sh
cp config/boot/boot.min.properties boot.local.properties
python app.py --config boot.local.properties
```

Open http://localhost:1234 ; admin/admin.

## Run tests

```sh
# all tests (updates config/version.txt, cleans testdata/)
python scripts/run-test.py

# focused targets (see scripts/run-test.py for full list)
python scripts/run-test.py app      # handlers
python scripts/run-test.py xutils   # xutils lib
python scripts/run-test.py note     # note handlers
python scripts/run-test.py xutils_db  # kv db layer
python scripts/run-test.py xutils_sqldb  # sql db layer

# bypass runner (pytest directly)
python -m pytest tests/test_app.py --doctest-modules --cov xnote_handlers --capture no
```

Test runner always runs `doctest-modules` and `--cov`. It uses `config/boot/boot.test.properties` (data dir = `./testdata/`).

## Architecture

| Layer | Directory | Role |
|-------|-----------|------|
| Entry | `app.py` / `main.py` | Delegates to `xnote.core.xnote_app.main()` |
| Core framework | `xnote/core/` | Routing, config, auth, templates, DB lifecycle |
| HTTP handlers | `xnote_handlers/` | All page & API handlers (note, fs, tools, plugins, system, etc.) |
| WebUI components | `xnote/webui/` | Python UI component library (Pagination, ListView, Card, etc.) |
| Utilities | `xutils/` | DB drivers, file I/O, text parsing, cache, date, etc. |
| Config | `config/boot/` | Properties files; `boot.test.properties` for tests |

## URL routing

Module-level `xurls` tuple auto-discovers handlers:

```python
xurls = (
    r"/path", MyHandler,
)
```

`xmanager` auto-discovers all modules under `xnote_handlers/` reading `xurls`. URL path is derived from module path. No central route table.

## Handler conventions

Handlers are classes with `GET(self)` / `POST(self)` etc. They use the webpy fork (`web`) for request/response. Return strings for HTML, return dict/list for JSON.

```python
class MyHandler:
    def GET(self):
        return xtemplate.render("path/to/template.html")
```

## Template engine (custom tornado fork)

Key custom tags:

```
{% init x = val %}      # globals()['x'] = val 仅当未定义时
{% set x = val %}       # 局部变量赋值
{% set-global x = val %} # 强制设置全局变量
{% from module import X %}  # Python import（不同于include）
{% render ui_component %}    # 调用 ui_component.render() 输出HTML
{% include path/to/file.html %}
```

Component rendering pattern:
```html
{% from xnote.webui import Pagination %}
{% render Pagination(**globals()) %}
```

## webui component framework (`xnote/webui/`)

Python-side UI components extend `BaseComponent` (`xnote/webui/base.py`), provide a `render()` method returning HTML string. In templates, import via `{% from xnote.webui import %}` and render via `{% render %}`.

Available: `Pagination`, `ListView`, `Card`, `Table`, `Form`, `TabBox`, `Div`, `TextLink`, `ActionLink`, `Input`, `Textarea`, `Panel`, etc.

## Properties config

Custom `.properties` parser (`xutils.text_parser_properties.py`). Types declared as `key.type = bool|int`. Example:

```properties
# name.type = bool | int | str
debug = false
debug.type = bool
```

**Never use `config/boot/boot.default.properties` directly** — code safe-guard prevents it.

## Key conventions

- **Test env**: `tests/test_base.py` calls `xconfig.init()` with `boot.test.properties`, uses SqliteKV, auto-logs-in admin. Define test classes extending `test_base.BaseTestCase`.
- **DB drivers**: sqlite (default, no deps), leveldbpy (Windows fallback), lmdb, mysql, ssdb. Minimal deps: `pip install -r config/requirements.min.txt` (just `six`).
- **Code style**: PEP8 + `docs/code_style.md`. Handler naming: `XxxHandler`, DAO: `XxxDao`, models: `XxxRecord`.
- **Version**: `config/version.txt` — auto-updated during test run (branch-date format).
- **Sentinel**: `sentinel.py` wraps the server; exit code 205 or 52480 triggers restart. Also respects `xnote-reboot.txt` file.
- **Migrations**: `xnote_migrate/` has numbered `upgrade_xxx.py` files for schema/data migration during version upgrades.
- **Build step**: Run `scripts/build.py` to build CSS/JS bundles before production (referenced in code, file may not exist at root).
