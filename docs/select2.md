# select2 使用说明

项目统一使用 [select2 4.0.13](https://select2.org/) 作为下拉选择组件。组件加载与初始化封装在公共模板
`xnote_handlers/common/script/load_select2.html` 中，**页面只需要声明 `data-*` 属性，不需要自己写初始化脚本**。

## 一、引入组件

在页面/表单模板里 include 公共脚本（同一模板内重复 include 只会生效一次）：

```html
{% include common/script/load_select2.html %}
```

它会完成三件事：

1. 加载 select2 的 CSS 与 JS；
2. 定义 `xnote.initSelect2()` 初始化函数；
3. 在 `$(document).ready` 时自动初始化一次。

### 弹窗表单必须单独考虑

编辑表单弹窗是通过 `xnote.table.handleEditForm` 拉取 HTML 片段后注入到对话框的，
而 **通过 html 注入的 `<script>` 不会执行**（见 `xnote-ui/x-dialog.js` 的 `success` 回调注释）。
弹窗里唯一会运行的刷新入口是 `xnote.refresh()` → `xnote.initSelect2()`。

因此有两条硬性约定：

- **列表页/承载弹窗的主页面**要保证 select2 库与 `xnote.initSelect2` 已加载。
  页面里渲染了 `DataTable`（→ `common/table/table.html` → `table_script.html`）时会自动带上，无需再写；
  没有表格的页面则需自行 include 一次。
- **弹窗返回的 HTML 片段**要 include 一次，保证该片段直接作为独立页面打开时同样可用
  （例如直接访问 `/note/relation?action=edit&note_id=xxx`，此时没有外层页面壳提供参考的脚本）。

> 反例：把 `$("#id").select2({ajax:...})` 直接写在编辑表单的内联 `<script>` 里。
> 在弹窗场景下这段脚本根本不会执行；即使执行，`xnote.execute()` 是立即执行，
> 此时 select2 可能还没加载完，会得到 `select2 is not a function` / `$(...).select2 未定义`。
> 这类初始化请一律走下面的 `data-*` 声明式用法。

参考 `NoteRelationHandler`：`EDIT_HTML` include 了 `load_select2.html`；其 `PAGE_HTML` 因渲染了
`DataTable` 已自动带上，故未重复 include。

## 二、普通下拉（指定选项）

渲染出的 `<select>` 会被自动初始化：

```python
row = form.add_row("类型", "type", type=FormRowType.select)
row.add_option("类型1", "1")
row.add_option("类型2", "2")
```

- 默认 `minimumResultsForSearch: 10`，**选项少于 10 个时不显示搜索框**。
- `dropdownParent` 自动取最近的 `.layui-layer-content`（弹窗容器），避免下拉被弹窗裁剪。
- select2 原生支持 `data-placeholder` 占位属性。
- 每个 select 只会初始化一次（已带 `select2-hidden-accessible` 类的会被跳过）。

不想让某个下拉被自动接管，加上 `data-disable-select2` 即可。

## 三、远程搜索下拉（ajax）

用于「关联笔记」这类需要按关键字搜索大量数据的场景。

### Python 侧

给表单行设置 `ajax_url`（必填）和 `ajax_data`（可选，额外的固定查询参数，JSON 字符串）：

```python
row = form.add_row("关联笔记", "target_id", type=FormRowType.select, value=str(relation.target_id))
row.ajax_url = "/api/v1/note/select_name"
row.ajax_data = jsonutil.to_json(dict(type="public"))

# 编辑已有记录时，回填当前值需要显式选中对应 option，否则 select2 无法回显
if note_name != "":
    row.add_option(title=note_name, value=str(relation.target_id), selected=True)
```

渲染结果：

```html
<select id="row_1_1" name="target_id" class="form-row-value" value="..."
        data-select2-ajax-url="/api/v1/note/select_name"
        data-select2-ajax-data='{"type":"public"}'>
    <option value="1615651200001" selected>某笔记</option>
</select>
```

### 前端行为

命中 `data-select2-ajax-url` 后，`xnote.initSelect2` 会初始化为 ajax 选择器：

- 每次搜索请求携带 `search=输入关键字`，再叠加 `data-select2-ajax-data` 里的额外参数；
- 不设置 `minimumResultsForSearch`，**始终显示搜索框**（否则下拉里没有选项时搜索框会被隐藏，看起来就是"搜索失效"）；
- `dropdownParent` 同样自动适配弹窗。

### 后端接口约定

接口必须返回 select2 要求的 `{results: [...]}` 结构，每项为 `{id, text}`：

```json
{"results": [{"id": "1615651200001", "text": "笔记标题"}]}
```

参考实现 `xnote_handlers/note/note_api.py` 的 `SelectNameHandler`（路径 `/api/v1/note/select_name`，
读取 `search` 参数，默认返回最多 100 条）。

按项目约定，笔记相关的 REST 接口统一放在 `note_api.py` 中，
路径使用 `/api/v1/note/{method}` 形式，并通过 `xurls` 注册。
（提示：`xmanager` 会对不符合模块前缀的路径打 WARN，但依然会注册成功，见 `xnote/core/xmanager.py`。）

若需要分页/滚动加载，返回结构里补充 `pagination.more`：

```json
{"results": [...], "pagination": {"more": true}}
```

## 四、属性速查

| 属性 | 作用 |
|------|------|
| `data-select2-ajax-url` | 声明为远程搜索下拉，值为搜索接口地址 |
| `data-select2-ajax-data` | 额外固定查询参数（JSON 字符串） |
| `data-disable-select2` | 跳过自动初始化，由业务代码自行处理 |
| `data-placeholder` | select2 原生占位文案 |

## 五、调试要点

搜索无反应时按以下顺序排查：

1. 页面/弹窗是否 include 了 `load_select2.html`（检查 `$.fn.select2` 是否存在）；
2. `<select>` 上是否有 `data-select2-ajax-url`；
3. 浏览器 Network 里搜索时是否有请求打到对应的 search 接口；
4. 接口返回是否为合法的 `{results: [...]}`;
5. 该 select 是否已被提前初始化成「无 ajax」版本（检查是否有 `select2-hidden-accessible` 类但下拉无搜索框）。
