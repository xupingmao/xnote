# AGENTS.md — xnote

## 编程规范

- 简单原则：如果满足需求目标有多个方案，优先选择简单的方案
- 职责单一原则：一个方法不要做多件事情
- 分层原则：按照view/biz/dao三层分层，简单场景可以直接view/dao两层
- 可自动化：开发完一个功能后，需要补充对应的自动化测试脚本并且测试通过
- 前端弹窗：alert/confirm/prompt 统一使用 `xnote` 模块的函数（`xnote.alert` / `xnote.confirm` / `xnote.prompt` / `xnote.toast`，定义于 `static/js/xnote-ui/x-dialog.js`），**不要直接使用** `window.alert` / `window.confirm` / `window.prompt`。这些函数是回调式的（非返回值）：`xnote.confirm(msg, function (ok) { if (ok) {...} })`，其中 `ok === true` 表示确认；`xnote.prompt(title, defaultValue, callback)` 在 `callback(newValue)` 中拿结果；无 layer 时内部才会回退到原生实现。
- 结构化对象优先：设计接口（函数/方法）的输入输出参数时，优先使用结构化的对象（自定义类，如 `XxxResult`/`XxxInfo`），而不是裸 `dict`。兼容 Python 3.6 不可用 `dataclass` 时，用普通类实现，并通过 `from_dict` / `to_dict` 与 JSON 互转；类的字段用类型注解明确标注。

## REST API 约定

- **接口位置**：笔记相关的后端 REST 接口统一放在 `xnote_handlers/note/note_api.py` 中，URL 路径统一使用 `/api/note/xxx` 形式（即 `/api/{module}/{method}`，例如获取笔记内容用 `/api/note/content`），不要散落到 `note_view.py` 等页面 handler 里。
- **成功判断**：前端（及测试）判断接口成功与否统一使用返回字段 `resp.success`（布尔值），不要使用 `resp.code == "success"`。`note_api.py` 中的接口统一通过 `webutil.SuccessResult` / `webutil.FailedResult` 返回，这两个方法已经同时设置 `success` 与 `code` 字段。

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

## 前端命令机制 (`xnote.executeCommands`)

**偏好**：新增带 DOM 更新的交互时，尽量由**后端用模板渲染好 HTML 片段**，再通过命令列表交给前端更新 DOM，**不要在前端手写字符串拼 HTML**（既能减少前端代码，也能借模板自动转义避免 XSS）。

- 命令是一个数组，每项形如 `{command, id|name, value, delay}`：
  - `command`：命令类型，见下
  - `id`：目标元素 id（优先用 id，`findElement` 生成 `$("[id=xxx]")`）;不传则按 `name` 查找 `$("[name=xxx]")`
  - `value`：命令参数（文本/HTML/提示语等）
  - `delay`：延迟执行毫秒数（可选，默认 0）
- 支持的类型：`update_value`(设置输入框值) / `update_text`(设置 text) / `update_html`(整体替换 innerHTML) / `append_html`(追加 HTML 片段) / `toast` / `alert` / `reload`。
- 前端调用：`xnote.executeCommands(resp.data.commands)`（命令内部用 `setTimeout` 异步执行，前端若要在 DOM 更新后操作，需同样延后一拍）。

后端组装方式（参考 `xnote_handlers/chatbot/chatbot_render.py`）：

```python
from typing import Any, Dict, List
import xtemplate

def render_message_rows(message_list):
    # type: (list) -> str
    # 注意 xtemplate.render 返回 bytes, 命令的 value 必须是 str
    html = xtemplate.render("chatbot/component/message_rows.html",
                            message_list=message_list)
    return html.decode("utf-8") if isinstance(html, bytes) else html

def build_send_commands(result):
    # type: (...) -> List[Dict[str, Any]]
    rows = render_message_rows([result.message, result.reply])
    return [{"command": "append_html", "id": "message-list", "value": rows}]
```

把 `commands` 作为字段放进返回的 `XxxResult`（`BaseDataRecord` 子类，随 JSON 自动序列化），前端 `onSendSuccess` 里 `xnote.executeCommands(data.commands)` 即可。

**JS 源文件注意**：`static/js/xnote-ui/x-init.js` 是带 JSDoc 的源码，`static/js/app.build.js` 是页面 `common/base_head.html` 实际加载的打包文件（已被 gitignore）。新增命令类型时需要**两处同步修改**。

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
- **类型检查**：增量代码需要通过 mypy 检查。改动后运行 `python -m mypy <改动的文件>`（配置见 `mypy.ini`），确保被改动的文件本身无类型错误；新增/修改的代码应补充类型注解。
- **Python 兼容性**：运行环境兼容 `Python >= 3.6`，新增代码请勿使用 3.7+ 语法（例如 `from __future__ import annotations`、内置泛型 `dict[str, Any]`/`list[int]` 等），请使用 `typing` 中的 `List`/`Dict`/`Optional`/`Union` 等；类属性注解（PEP 526）可用。
- **Version**: `config/version.txt` — auto-updated during test run (branch-date format).
- **Sentinel**: `sentinel.py` wraps the server; exit code 205 or 52480 triggers restart. Also respects `xnote-reboot.txt` file.
- **Migrations**: `xnote_migrate/` has numbered `upgrade_xxx.py` files for schema/data migration during version upgrades.
- **Build step**: Run `scripts/build.py` to build CSS/JS bundles before production (referenced in code, file may not exist at root).
- **JS 语法兼容 ES3**: `static/js/` 下的运行时代码必须兼容 ES3 语法（只用 `var`、函数声明、`function` 表达式，不用 `let`/`const`/箭头函数/模板字符串/`class` 等 ES5+ 语法），以适配老旧浏览器/引擎。测试脚本（`tests/js/`）不受此限制，可使用现代 JS 语法。
- **模板引擎导入**: 使用 `from xnote.core import xtemplate`，不要直接 `import xtemplate`（当前兼容但不推荐，后续可能移除顶层别名）。
