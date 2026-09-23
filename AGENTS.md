# AGENTS.md — xnote

## 编程规范

- 简单原则：如果满足需求目标有多个方案，优先选择简单的方案
- 职责单一原则：一个方法不要做多件事情
- 分层原则：按照view/biz/dao三层分层，简单场景可以直接view/dao两层
- 可自动化：开发完一个功能后，需要补充对应的自动化测试脚本并且测试通过
- 页面默认带标题栏：每个页面（页面 handler / 模板）默认都应在页面顶部渲染标题栏，统一使用公共组件 `common/title/base_title.html`（`{% include common/title/base_title.html %}`），通过 `kw.title` / `kw.parent_link` / `kw.right_link` / `kw.back_url` 控制内容。不要在业务模板里自己手写页面级标题栏 DOM 替代它；若页面内另有业务相关的工具条（如 chatbot 移动端的「☰ 会话」切换 + 当前会话标题），保留在原位置即可，不要为了套用标题栏而改动原有交互。标题文本所在 `<span>` 的 `id` 固定为 `chat-mobile-title`，后端可通过 `update_text` 命令同步更新移动端标题。
- 前端弹窗：alert/confirm/prompt 统一使用 `xnote` 模块的函数（`xnote.alert` / `xnote.confirm` / `xnote.prompt` / `xnote.toast`，定义于 `static/js/xnote-ui/x-dialog.js`），**不要直接使用** `window.alert` / `window.confirm` / `window.prompt`。这些函数是回调式的（非返回值）：`xnote.confirm(msg, function (ok) { if (ok) {...} })`，其中 `ok === true` 表示确认；`xnote.prompt(title, defaultValue, callback)` 在 `callback(newValue)` 中拿结果；无 layer 时内部才会回退到原生实现。
- 字符串格式化：优先使用 **f-string**（如 `f"hello {name}"`）；`%` 格式化与 `str.format()` 是旧用法，**新代码不推荐**。日志/异常中需要延迟格式化时才允许用 `%`（如 `logging.warning("count=%s", count)`）。
- JSON 处理统一走 `xutils.jsonutil`：新代码**不要直接 `import json` 再调用 `json.dumps` / `json.loads`**，统一使用 `jsonutil.to_json(obj)` 序列化、`jsonutil.from_json(str)` 或 `jsonutil.parse_json_to_dict(str)` 反序列化（后者断言结果必须是 dict）。原因是 `to_json` 使用 `jsonutil.MyEncoder`，能安全转换 `datetime` / `date` / `bytes` / `UUID` 等特殊类型的字段（如把整条记录做成 JSON 快照时，`json.dumps` 遇到这些字段会抛 `TypeError`），同时统一了 `ensure_ascii=False` 与紧凑分隔符的行为，避免各模块产出的 JSON 格式不一致。反序列化失败时按业务降级处理（如返回 `{}`）并打日志，不要把解析异常抛给调用方。
- 结构化对象优先：设计接口（函数/方法）的输入输出参数时，优先使用结构化的对象（自定义类，如 `XxxResult`/`XxxInfo`），而不是裸 `dict`。兼容 Python 3.6 不可用 `dataclass` 时，用普通类实现，并通过 `from_dict` / `to_dict` 与 JSON 互转；类的字段用类型注解明确标注。
- 小模板内联：小于 20 行的 HTML 模板直接放在 Python 代码里，用 `xtemplate.render_text(text, template_name, **kw)` 渲染，不要单独建 `.html` 模板文件。大于 20 行的模板才放 `xnote_handlers/` 下单独的模板文件中。
- webui 组件 CSS 放公共文件：`xnote/webui/` 下的组件是公共组件，其样式不要写在业务模块的 css 里，统一放到 `static/css/base/common-*.css`（例如下拉/更多操作菜单放 `common-dropdown.css`）。注意 `common-*.css` 经打包进入 `static/css/app.build.css`（全局加载），但若未重新执行构建脚本，本地开发可在使用组件的页面直接 `<link>` 该 `common-*.css` 使其立即生效。
- **间距优先用内置工具类**：间距工具类（padding / margin）统一收在 `static/css/base/common-spacing.css`，不要散落到各组件 css。里面是 Tailwind 风格的一套：`p-`/`px-`/`py-`/`pt-`/`pr-`/`pb-`/`pl-` 与 `m-`/`mx-`/`my-`/`mt-`/`mr-`/`mb-`/`ml-`，刻度为 `n*4px`，另含 `mx-auto`/`ml-auto`/`mr-auto`/`my-auto`。写页面/组件的内外边距时**优先在 HTML 里组合这些类，不要再新造 `.padding-*`/`.margin-*` 之类的别名**（文件里保留的历史别名 `padding-sm`/`margin-top-md`/`top-offset-1` 等仅为兼容，新代码不要用）。取值遵守 `docs/code_style_css.md` 的 8px 栅格，即**用偶数档**（`px-2`=8px、`px-4`=16px、`px-6`=24px）；`p-1`(4px) 属半步、只用于紧凑组件微调，不用 `px-3`/`px-5`（12/20px 不在栅格上）。改动 `common-spacing.css` 后必须重建产物 `python -c "import sys; sys.path.insert(0,'.'); from xnote.core import xnote_code_builder as b; b.build_app_css()"`，否则页面读到的还是旧的 `app.build.css`。
- webui 组件模块默认私有，统一由 `__init__.py` 对外暴露：`xnote/webui/` 下的组件模块**默认都是私有的**，新增/重构组件时，组件类必须在该包的 `xnote/webui/__init__.py` 里**显式导出**（如 `from ._tag_select import TagSelect`、`from ._list import ListView`），业务代码通过 `from xnote.webui import ...` 或更上层的 `xnote.plugin` 使用，**不要直接 import 内部模块路径**（如 `from xnote.webui._list import ListView`、`import xnote.webui._tag_select`）。模块名用下划线前缀（如 `_list.py` / `_pagination.py` / `_image.py` / `_tag_select.py`）表达私有模块；没有前缀的内部模块（如 `form.py` / `component.py`）同样视为内部模块，不对外直接 import。
- **不要自行提交 git commit**：仅在用户明确要求提交时才执行 `git commit`（例如用户说"提交代码"）。其余情况下只修改工作区文件，不要主动 `git add` / `git commit`，把提交时机交给用户。
- 浅灰标签慎用：`TextTag(css_class="lightgray")`（背景 `#eee`，见 `_static/css/base/common-tag.css`）与列表行的 hover 背景同色（`.list-item:hover` 也是 `#eee`，见 `common-list.css`），**不要在有 hover 效果的组件上使用**（例如列表行 `ListViewItem` 的标签），否则 hover 时标签会“消失”。列表内的日期等元信息改用无背景的 `TextSpan(css_class="todo-time")` 之类的纯文本样式。
- 类型判断必须依赖显式标识：**不要根据 ID 数值范围（如 `id >= OFFSET`）来区分不同类型的数据**（例如笔记评论 vs 待办评论）。ID 一旦增长到超过预设区间就会误判，且区间偏移量只是存储换算手段、不代表真实类型。区分类型应依赖请求/记录上的**显式字段**（如评论的 `type`、列表的 `list_type` 等），由调用方在创建/查询时显式传入，后端据此路由。

## 测试规范

- **只测数据和逻辑，不测样式/DOM 结构**：测试的目标是验证数据与逻辑的正确性（DAO 增删改查、状态流转、计数、过滤/分页条件、接口返回字段、权限校验等），**不要为 CSS 样式、布局结构写测试**。例如不要断言 `class="list-item-line has-icon"`、元素渲染顺序、`align-items` 之类的样式细节 —— 这类断言与实现强耦合，改一次样式就要改一堆测试，且无法反映功能是否正确。测试应断言**内容与行为**：数据是否写入/更新、计数是否正确、返回的字段值是否符合预期、链接是否指向正确的业务地址（如 `href` 指向的 task_id/project_id 是否正确）等。
- 测试接口时 HTTP 参数需 quote：测试调用 REST/页面接口构造 URL 时，查询参数（尤其是含中文/非 ASCII 字符）必须经过 URL 编码，使用 `xutils.quote`（即 `urllib.parse.quote`），否则服务端按字节解码会出错，导致查询/匹配失败。例如按关键词搜索 `GET /api/v1/todo/list?key=水果` 必须写成 `f"/api/v1/todo/list?key={quote('水果')}"`，不能直接把原始中文拼进 URL。

## REST API 约定

- **接口位置**：笔记相关的后端 REST 接口统一放在 `xnote_handlers/note/note_api.py` 中，URL 路径统一使用 `/api/{version}/{module}/{method}` 形式（当前版本为 `v1`，例如获取笔记内容用 `/api/v1/note/content`），不要散落到 `note_view.py` 等页面 handler 里。所有模块的 REST 接口都要带版本号前缀（即 `/api/v1/{module}/{method}`），旧的 `/api/{module}/{method}`（无版本）已失效（直接 404）。
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

## 全局搜索组件（顶部导航搜索框）

顶部导航栏（`common/nav/base_nav_top.html`）内置一个全局搜索框（`common/search/search_box.html`）。页面 handler 只需设置 `xnote.core.xtemplate.BasePlugin` 的几个属性，就能让该搜索框定向搜索当前模块的数据，**不要自己再写页面级搜索输入框**：

- `self.search_action`：搜索表单提交地址（默认 `/search`）。如待办模块设为 `/todo`。
- `self.search_placeholder`：搜索框占位符。
- `self.search_ext_dict`：追加到搜索表单的隐藏参数 dict（用于限定搜索范围，如 `project_id` / `status` 等）。
- `self.search_type`：搜索类型（可选）；`self.show_search` 控制是否显示（默认 True）。

这些属性经 `BasePlugin.convert_attr_to_kw()` 注入模板全局变量，顶部导航的搜索框据此渲染 `action` 与隐藏字段（`search_box.html` 会遍历 `search_ext_dict` 输出隐藏 input）。

示例（待办模块 `TaskListPlugin`）：

```python
# 在当前项目内搜索全部状态的待办
self.search_action = "/todo"
self.search_placeholder = T("搜索待办")
if project_id > 0:
    self.search_ext_dict = dict(project_id=str(project_id), status=STATUS_FILTER_ALL)
else:
    # 跨项目搜索（project_id 不传，DAO 侧按 project_id=None 实现不过滤）
    self.search_ext_dict = dict(model="task", status=STATUS_FILTER_ALL)
```

搜索框提交后经 `?key=关键词&...` 回到本模块页面，handler 用 `xutils.get_argument_str("key", "")` 读取并做 `content LIKE` 模糊匹配即可；分页组件会自动保留 `key` 参数。

> 模板读取请求参数的写法：原 `{{?key}}` 是一种 try-catch 语法糖（取值失败回退为 `""`），现已统一改为 `{% init key = "" %}` 声明默认值后直接 `{{key}}`（搜索框组件 `search_box.html` 已采用）。**新代码不要再使用 `{{?x}}` 语法**，用 `{% init x = "" %}` + `{{x}}` 替代。

## 默认综合搜索（search 事件）与聚合结果

顶部全局搜索的【默认】（综合）搜索通过 `xmanager.fire("search", ctx)` 触发，所有用 `@xmanager.searchable(pattern, description=...)` 装饰的处理器都会收到 `SearchContext` 并各自往结果桶里追加 `SearchResult`。分类搜索（`search_type=note/dict/task/message/comment`）走 `SearchHandler.do_search_by_type`，**不会**触发 `search` 事件。

`SearchContext` 的结果桶按优先级拼接（`join_as_files()`）：`commands` → `tools` → `dicts` → `messages` → `notes` → `files`。

- **聚合（折叠）结果统一放在 `ctx.tools`**：当某类数据在综合搜索里不逐条展开、而是折叠成一条摘要时（例如【随手记】的 `搜索到[N]条随手记`、待办的 `搜索到[N]个待办`），结果 `SearchResult` 要 `append` 到 `ctx.tools`（放在靠前位置，降低被分页 20 条上限截断的概率），并设 `show_more_link=True`、链接指向该模块的列表/检索页。不要逐条 `append` 到 `ctx.notes`/`ctx.messages`。
- 普通逐条结果按模块性质放入 `notes` / `messages` 等桶。

示例（待办模块的折叠处理器 `xnote_handlers/todo/todo_search.py`）：

```python
@xmanager.searchable(".+", description="搜索待办")
def search_todo(ctx: SearchContext, expression=None):
    key = ctx.key
    if not key or ctx.user_id == 0:
        return
    total = TodoDao.count_with_filters(ctx.user_id, key=key)
    if total == 0:
        return
    item = SearchResult()
    item.name = f"搜索到[{total}]个待办"
    item.url = xconfig.WebConfig.server_home + "/todo?model=task&key=" + xutils.quote(key) + "&status=all"
    item.icon = "fa fa-check-square-o"
    item.category = "task"
    item.show_more_link = True
    item.show_move = False
    ctx.tools.append(item)   # 聚合结果放 tools 桶
```

## webui component framework (`xnote/webui/`)

Python-side UI components extend `BaseComponent` (`xnote/webui/base.py`), provide a `render()` method returning HTML string. In templates, import via `{% from xnote.webui import %}` and render via `{% render %}`.

Available: `Pagination`, `ListView`, `Card`, `Table`, `Form`, `TabBox`, `Switch`, `Div`, `TextLink`, `ActionLink`, `Input`, `Textarea`, `Panel`, `BlockTitle`, `ActionButton`, `RawHtml`, `TextSpan`, `Checkbox`, etc.

> 组件模块的可见性：上文"webui 组件模块默认私有，统一由 `__init__.py` 对外暴露"约定要求——新增组件类必须先在 `xnote/webui/__init__.py` 中 `from .xxx import Yyy` 导出，业务侧再 `from xnote.webui import Yyy`（或 `xnote.plugin`）使用，严禁直接 import 内部模块路径（见编码规范）。

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
- **枚举型字段用 `add_tag_select`（EnumItem 数量 <= 5）**：编辑表单里取值来自 `BaseEnum.enums()` 的枚举字段（如状态、优先级），**枚举项数量 <= 5 时优先用 `DataForm.add_tag_select()`**（tag 点选），而不是 `add_select`/`FormRowType.select`。选项仍是 `row.add_option(e.name, e.value)`，用法与 `add_select` 一致；默认单选，多选传 `multiple=True`。数量 > 5 或选项来自动态数据（如项目列表、笔记本列表）时仍用 `add_select`。参考 `xnote_handlers/todo/todo_view.py`（待办的状态/优先级、项目的状态）。
  ```python
  status_row = form.add_tag_select(title=T("状态"), field="status", value=task.status)
  for e in TodoStatusEnum.enums():
      status_row.add_option(e.name, e.value)
  ```
- **布尔字段用 `add_switch`（开关）**：编辑表单里的二态字段（启用/禁用、是否公开等）用 `DataForm.add_switch(title=..., field=..., checked=...)`，不要退化成 `add_select` 的「是/否」下拉。开关组件（`Switch`）也可独立使用（`from xnote.plugin import Switch`），**值的唯一来源是它渲染的隐藏域**（默认开=`true`、关=`false`，可用 `on_value`/`off_value` 自定义），由 `x-switch.js` 在点击时同步；用隐藏域而不是原生 checkbox，是因为 DataForm 的 `formData()` 取 `.val()`，checkbox 未选中时仍会提交 `value`，无法表达关闭状态。服务端取值用 `webutil.get_argument_str(field, "false")`。案例见 `/examples/switch`。
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
- **命令接口的返回值必须用 `webutil.CommandsResult`，不要手拼 `webutil.SuccessResult(data={"commands": [...]})`**（`CommandsResult` 继承 `WebResult`，预设 `success=True` 且 `data` 即 `List[CommandItem]`；自带 `add_command` / `add_reload_command` / `add_toast_command` 辅助方法）。单条命令用 `result.data.append(cmd)`，多条命令直接 `result.data = commands`（或 `result.data.extend(commands)`）。不要为了附带额外字段而在 `data` 里塞 `commands` 子键——若业务确需回传额外数据，应改用结构化对象（`XxxResult`）而非 `CommandsResult`。
- 前端调用：`xnote.executeCommands(resp.data)`（命令内部用 `setTimeout` 异步执行，前端若要在 DOM 更新后操作，需同样延后一拍）。注意：`CommandsResult` 的 `data` **就是命令数组本身**，不再有 `resp.data.commands` 这层嵌套。

后端组装方式（参考 `xnote_handlers/chatbot/chatbot_render.py`）：

```python
from typing import Any, List
from xnote.core import xtemplate
from xutils import webutil

def render_message_rows(message_list: List[Any]) -> str:
    # 注意 xtemplate.render_text 返回 bytes, 命令的 value 必须是 str
    html = xtemplate.render_text(_MESSAGE_ROWS_TEMPLATE, message_list=message_list)
    return html.decode("utf-8") if isinstance(html, bytes) else html

def build_send_commands(result: Any) -> List[webutil.CommandItem]:
    rows = render_message_rows([result.message, result.reply])
    return [webutil.CommandItem(command="append_html",
                                id="message-list", value=rows)]
```

把命令列表作为返回值直接交给前端：后端构造 `webutil.CommandsResult()`，用 `result.data.append(cmd)` / `result.data = commands` 填充命令，前端 `onSendSuccess` 里 `xnote.executeCommands(resp.data)` 即可（`resp.data` 即命令数组）。

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
- **类型标注一律用语法标注，不用注释式**：新增代码的类型必须用 **Python 语法支持的类型标注**表达（PEP 484 函数签名 / PEP 526 变量与属性注解），**不要写注释式标注**（`# type: (str) -> int`、`x = []  # type: List[str]`）：
  ```python
  # 推荐
  def add_url_param(url: str, name: str, value: int) -> str: ...

  class DataTable:
      def __init__(self):
          self.rows: List[TableRowType] = []
          self.pagination: Optional[Pagination] = None

  # 不推荐（注释式）
  def add_url_param(url, name, value):
      # type: (str, str, int) -> str
      ...
  ```
  原因是语法标注是语言的一部分，mypy / IDE / `typing.get_type_hints()` 都能直接读到，改签名时不会像注释那样被漏改而与实际代码脱节。存量代码里的注释式标注不必专门清理，但**改动到那段代码时顺手迁移成语法标注**。
- **Python 兼容性**：运行环境兼容 `Python >= 3.6`，新增代码请勿使用 3.7+ 语法（例如 `from __future__ import annotations`、内置泛型 `dict[str, Any]`/`list[int]` 等），请使用 `typing` 中的 `List`/`Dict`/`Optional`/`Union` 等；函数签名注解（PEP 484）与类属性注解（PEP 526）均可用，且**类型必须用语法标注表达，不要写 `# type:` 注释式标注**（见上文"类型标注一律用语法标注"）。
- **Version**: `config/version.txt` — auto-updated during test run (branch-date format).
- **Sentinel**: `sentinel.py` wraps the server; exit code 205 or 52480 triggers restart. Also respects `xnote-reboot.txt` file.
- **Migrations**: `xnote_migrate/` has numbered `upgrade_xxx.py` files for schema/data migration during version upgrades.
- **Build step**: Run `scripts/build.py` to build CSS/JS bundles before production (referenced in code, file may not exist at root).
- **JS 语法兼容 ES3**: `static/js/` 下的运行时代码必须兼容 ES3 语法（只用 `var`、函数声明、`function` 表达式，不用 `let`/`const`/箭头函数/模板字符串/`class` 等 ES5+ 语法），以适配老旧浏览器/引擎。测试脚本（`tests/js/`）不受此限制，可使用现代 JS 语法。
- **模板引擎导入**: 使用 `from xnote.core import xtemplate`，不要直接 `import xtemplate`（当前兼容但不推荐，后续可能移除顶层别名）。
- **不要污染模板全局命名空间**: `xnote/core/xtemplate.py` 的 `NAMESPACE` 只保留跨页面通用的少数几项（`format_date`/`format_time`/`quote` 等），**不要为了某个模板/组件往里加工具函数**。需要用到的函数在使用处局部注入即可：组件内部的模板在 `render()` 里作为模板变量传入（如 `self._template.generate(add_url_param=add_url_param, ...)`），独立的 `.html` 模板用 `{% from xutils.textutil import add_url_param %}` 按需导入。
