# AGENTS.md — xnote

## 编程规范

- 简单原则：如果满足需求目标有多个方案，优先选择简单的方案
- 职责单一原则：一个方法不要做多件事情
- 分层原则：按照view/biz/dao三层分层，简单场景可以直接view/dao两层
- 可自动化：开发完一个功能后，需要补充对应的自动化测试脚本并且测试通过
- 前端弹窗：alert/confirm/prompt 统一使用 `xnote` 模块的函数（`xnote.alert` / `xnote.confirm` / `xnote.prompt` / `xnote.toast`，定义于 `static/js/xnote-ui/x-dialog.js`），**不要直接使用** `window.alert` / `window.confirm` / `window.prompt`。这些函数是回调式的（非返回值）：`xnote.confirm(msg, function (ok) { if (ok) {...} })`，其中 `ok === true` 表示确认；`xnote.prompt(title, defaultValue, callback)` 在 `callback(newValue)` 中拿结果；无 layer 时内部才会回退到原生实现。
- 字符串格式化：优先使用 **f-string**（如 `f"hello {name}"`）；`%` 格式化与 `str.format()` 是旧用法，**新代码不推荐**。日志/异常中需要延迟格式化时才允许用 `%`（如 `logging.warning("count=%s", count)`）。
- 结构化对象优先：设计接口（函数/方法）的输入输出参数时，优先使用结构化的对象（自定义类，如 `XxxResult`/`XxxInfo`），而不是裸 `dict`。兼容 Python 3.6 不可用 `dataclass` 时，用普通类实现，并通过 `from_dict` / `to_dict` 与 JSON 互转；类的字段用类型注解明确标注。
- 小模板内联：小于 20 行的 HTML 模板直接放在 Python 代码里，用 `xtemplate.render_text(text, template_name, **kw)` 渲染，不要单独建 `.html` 模板文件。大于 20 行的模板才放 `xnote_handlers/` 下单独的模板文件中。
- webui 组件 CSS 放公共文件：`xnote/webui/` 下的组件是公共组件，其样式不要写在业务模块的 css 里，统一放到 `static/css/base/common-*.css`（例如下拉/更多操作菜单放 `common-dropdown.css`）。注意 `common-*.css` 经打包进入 `static/css/app.build.css`（全局加载），但若未重新执行构建脚本，本地开发可在使用组件的页面直接 `<link>` 该 `common-*.css` 使其立即生效。

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

Available: `Pagination`, `ListView`, `Card`, `Table`, `Form`, `TabBox`, `Div`, `TextLink`, `ActionLink`, `Input`, `Textarea`, `Panel`, `BlockTitle`, `ActionButton`, `RawHtml`, `TextSpan`, `Checkbox`, etc.

### 优先用组件开发页面

**偏好**：新增/重构带 UI 的页面时，优先用 `xnote/webui` 里的组件拼装页面，而不是直接手写大段 HTML。handler 里 `import` 组件、构造好 `kw` 传进模板，模板里只写 `{% render xxx %}`。这样组件集中维护、便于复用与改样式。

- **统一从 `xnote.plugin` 导入**（它是 `xnote.webui` 的再导出，已补齐常用组件）：`from xnote.plugin import TabBox, BlockTitle, Input, ActionButton, RawHtml, Div, ...`。避免业务代码直接依赖 `xnote.webui` 内部路径。
- 组件用法（handler 侧组装，模板侧渲染）：
  ```python
  from xnote.plugin import TabBox, BlockTitle, Input, ActionButton, RawHtml

  kw.title_component = BlockTitle(text=T("待办"))
  kw.create_input = Input(id="todo-content", name="content", placeholder=T("添加待办"))
  kw.create_button = ActionButton(text=T("添加"), onclick="TodoView.create()")
  # 需要 JS 挂载点的空 div，用 RawHtml 直接输出，不要用 Div 组件
  # （Div/BaseContainer 在没有任何 children/html 时 render 返回 ""，挂载点会消失）
  kw.body_component = RawHtml('<div id="todo-body" class="todo-body"></div>')
  ```
  ```html
  {% render title_component %}
  <div class="todo-create">
      {% render create_input %}
      {% render create_button %}
  </div>
  {% render body_component %}
  ```
- 筛选用 **TabBox**（不是 `<select>`/Dropdown）。`TabBox(tab_key=..., tab_default=...)` + `add_item(title, value, href)`，href 互相保留其余筛选参数；客户端 `x-tab.js` 按 URL 参数 `data-tab-key` 自动高亮（参考 `xnote_handlers/todo/todo_view.py` 的 `_build_filter_html`）。
- 组件样式统一放 `static/css/base/common-*.css`（见上文"webui 组件 CSS 放公共文件"）。

### 列表/CRUD 页面优先用 `ListView`（`BaseListPlugin`）

**偏好**：列表、增删改查类页面优先用 `xnote/plugin/list_plugin.py` 的 `BaseListPlugin` + `xnote/webui` 的 `ListView`/`ListViewItem` 服务端渲染列表，不要手写 `.html` 模板 + 大量前端 JS 拼 DOM。参考 `xnote_handlers/todo/todo_view.py`（`ProjectListPlugin` / `TaskListPlugin`）。需要表格形态时才用 `BaseTablePlugin`（`xnote/plugin/table_plugin.py`）。

- 继承 `BaseListPlugin`，重写 `handle_page()`：`list_view = self.create_list_view()` → `ListViewItem(...)` 逐条 `add_item`。
- `ListViewItem` 继承 `TextContainer`，可用 `add_span(text, css_class)` / `add_link(text, href)` / `add_br()` / `add_item_sep()`；`item.tags` 放 `TextTag(text, css_class)`（样式类：`red`/`orange`/`gray`/`lightblue`/`lightgray`/`lightred`/`lightpurple`，定义于 `static/css/base/common-tag.css`）；`item.extra`（右浮动）放操作组件。
- 行操作用 `EditFormActionLink(text, url)`（GET `?action=edit` 弹表单）与 `ConfirmActionLink(text, url, msg)`（确认框 + AJAX 后自动 reload）；它们依赖 `xnote.table.handleEditForm` / `handleConfirmAction`（在全局 `app.build.js` 内）。
- **【删除】等破坏性操作链接用红色**：统一传 `css_class="red"`（`ConfirmActionLink(text="删除", url=..., msg=..., css_class="red")`，颜色规则见 `static/css/base/common.css` 的 `.red`）。不要用 `danger`——`.danger` 只对带 `btn` 类的按钮生效（`.btn.danger`），挂在操作链接上不会变红。
- **整行链接 vs 两行布局**：给 `ListViewItem` 传 `href` 会渲染成"整行链接"（外层 `<a>`）；此时 `item.extra` 由组件渲染在 `<a>` **之外**，配合 `common-list.css` 的 `.list-item-outer` flex 规则固定在右侧（所以 href + 操作按钮是合法的，不会 `<a>` 嵌套）。如果希望操作区位于内容**下方**（两行布局），则不要传 `href`，改用 `add_link` 在内容里放链接，操作区放进第二个 `Div`（参考 `todo_view.py::TaskListPlugin`）。
- **注意 `require_admin` 默认 True**：非管理员的业务页面要显式设 `require_admin = False`（`require_login` 默认 True）。
- **增删改**：`handle_edit()` 用 `create_form()`(`DataForm`) 组装表单并 `response_form(form=form)`；表单提交回 `form.path?model=xxx&action=save`，在 `handle_save()` 里用 `self.get_data_dict()`(ParamDict) 取 `data` JSON。`handle_delete()` 返回 `webutil.SuccessResult()` 即可（前端 `confirm` 动作会 reload）。
- 自定义页面结构（如列表上方加筛选 Tab）用类属性 `page_html` 覆盖（`BaseListPlugin.get_page_html()` 返回它），把 `filter_html` 通过 `response_page()` 传入。
- 创建按钮放标题栏右侧：`self.option_html = EditFormButton(text="新建", url="?action=edit").render()`。
- 侧边栏：`self.update_aside("{% include common/sidebar/app_index.html %}")`。
- 同一个 URL 需要按参数渲染不同列表时，可用一个薄的普通 handler（带 `@xauth.login_required()`）在 `GET/POST` 里按参数实例化对应插件并返回 `Plugin().GET()`（参考 `TodoIndexHandler`）。

<details>
<summary>表格形态：`BaseTablePlugin`</summary>

- 继承 `BaseTablePlugin`，重写 `handle_page()`，用 `DataTable` 组装：`add_head(title, field, ...)`、`add_row(dict)`、`add_action(title, type=..., link_field=..., msg_field=...)`；创建按钮放 `table.action_bar.add_edit_button(text, url)`。
- 行操作用 `TableActionType`：`link`、`confirm`、`edit_form`、`button`；行字段值为 `None`/`""` 时该操作不渲染。
- 自定义页面结构用 `PAGE_HTML = "{% raw filter_html %}" + BaseTablePlugin.TABLE_HTML`。
</details>

## 前端命令机制 (`xnote.executeCommands`)

**偏好**：新增带 DOM 更新的交互时，尽量由**后端用模板渲染好 HTML 片段**，再通过命令列表交给前端更新 DOM，**不要在前端手写字符串拼 HTML**（既能减少前端代码，也能借模板自动转义避免 XSS）。

- 命令是一个数组，每项形如 `{command, id|name, value, delay}`：
  - `command`：命令类型，见下
  - `id`：目标元素 id（优先用 id，`findElement` 生成 `$("[id=xxx]")`）;不传则按 `name` 查找 `$("[name=xxx]")`
  - `value`：命令参数（文本/HTML/提示语等）
  - `delay`：延迟执行毫秒数（可选，默认 0）
- 支持的类型：`update_value`(设置输入框值) / `update_text`(设置 text) / `update_html`(整体替换 innerHTML) / `append_html`(追加 HTML 片段) / `toast` / `alert` / `reload`。
- **命令项必须用 `webutil.CommandItem` 构造，不要直接拼 dict**（`webutil.CommandItem(command=..., id=..., value=..., delay=...)` 继承 `web.Storage`，随 JSON 自动序列化，字段更明确、不易拼错 key）。
- 前端调用：`xnote.executeCommands(resp.data.commands)`（命令内部用 `setTimeout` 异步执行，前端若要在 DOM 更新后操作，需同样延后一拍）。

后端组装方式（参考 `xnote_handlers/chatbot/chatbot_render.py`）：

```python
from typing import List
from xnote.core import xtemplate
from xutils import webutil

def render_message_rows(message_list):
    # type: (list) -> str
    # 注意 xtemplate.render_text 返回 bytes, 命令的 value 必须是 str
    html = xtemplate.render_text(_MESSAGE_ROWS_TEMPLATE, message_list=message_list)
    return html.decode("utf-8") if isinstance(html, bytes) else html

def build_send_commands(result):
    # type: (...) -> List[webutil.CommandItem]
    rows = render_message_rows([result.message, result.reply])
    return [webutil.CommandItem(command="append_html",
                                id="message-list", value=rows)]
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
- **Code style**: PEP8 + `docs/code_style.md`. Handler naming: `XxxHandler`, DAO: `XxxDao`, 数据库模型(model): `XxxRecord`（**统一用 `Record` 后缀**，不要用 `DO`/`Model` 等后缀；历史遗留的 `MessageDO`/`NoteDO` 等属于旧风格，新代码请遵循 `XxxRecord` 约定）。
- **数据库模型主键命名风格**：新表的**主键列名**统一用 `<实体名>_id` 形式（例如 `todo_task` 表主键用 `task_id`、`todo_project` 表主键用 `project_id`），**不要用泛化的 `id`**。建表时通过 `xtables.create_default_table_manager(table_name, pk_name="task_id", ...)` 的 `pk_name` 参数声明；模型类 `XxxRecord` 用 `self.task_id = 0` 声明字段，并在 `_ignore_save_fields = ["task_id"]` 排除（自增主键插入时由 DB 生成，不写）。DAO 的 `where` / `save.pop(...)` / 前端传参（`task_id`/`project_id`）与 JSON 返回字段全部对齐该命名。
- **数据库时间字段**：时间字段统一使用 `bigint` 类型，保存**毫秒时间戳**（而不是 datetime 字符串），与 DB 无关、跨库一致；字段命名统一用 **`create_time` / `update_time`**（`ctime` / `mtime` 是旧用法，**新表不要再使用**）。写入用 `dateutil.timestamp_ms()`（返回 `int(time.time()*1000)`），展示用 `dateutil.format_millis(ms)`。建表时 `manager.add_column("create_time", "bigint", default_value=0, comment="创建时间(毫秒时间戳)")`，模型类 `self.create_time = 0`。参考 `chat_session` / `note_fragment`。历史遗留的 datetime 字符串时间字段（如有）按新旧约定共存于旧表，新表不要再引入。
- **DAO 新增数据**：DAO 层新增记录**优先使用 `table.insert_record(record)`**（传入 `XxxRecord` 模型对象，内部调用 `record.to_save_dict()` 做字段过滤），**不建议直接使用 `table.insert(**save_dict)`** 手拼字典。仅当需要显式指定主键等特殊场景（例如从消息迁移、用 msg_id 作为 task_id）才直接用 `insert`，参考 `TodoDao.create_with_id`。
- **类型检查**：增量代码需要通过 mypy 检查。改动后运行 `python -m mypy <改动的文件>`（配置见 `mypy.ini`），确保被改动的文件本身无类型错误；新增/修改的代码应补充类型注解。
- **Python 兼容性**：运行环境兼容 `Python >= 3.6`，新增代码请勿使用 3.7+ 语法（例如 `from __future__ import annotations`、内置泛型 `dict[str, Any]`/`list[int]` 等），请使用 `typing` 中的 `List`/`Dict`/`Optional`/`Union` 等；类属性注解（PEP 526）可用。
- **Version**: `config/version.txt` — auto-updated during test run (branch-date format).
- **Sentinel**: `sentinel.py` wraps the server; exit code 205 or 52480 triggers restart. Also respects `xnote-reboot.txt` file.
- **Migrations**: `xnote_migrate/` has numbered `upgrade_xxx.py` files for schema/data migration during version upgrades.
- **Build step**: Run `scripts/build.py` to build CSS/JS bundles before production (referenced in code, file may not exist at root).
- **JS 语法兼容 ES3**: `static/js/` 下的运行时代码必须兼容 ES3 语法（只用 `var`、函数声明、`function` 表达式，不用 `let`/`const`/箭头函数/模板字符串/`class` 等 ES5+ 语法），以适配老旧浏览器/引擎。测试脚本（`tests/js/`）不受此限制，可使用现代 JS 语法。
- **模板引擎导入**: 使用 `from xnote.core import xtemplate`，不要直接 `import xtemplate`（当前兼容但不推荐，后续可能移除顶层别名）。
