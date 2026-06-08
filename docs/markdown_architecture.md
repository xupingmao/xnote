# xnote Markdown 处理架构

> 总结于 2026-06-08，涵盖整个项目中 Markdown 的存储、编辑、渲染、预览流程。

---

## 1. 依赖与库

| 组件 | 说明 | 位置 |
|------|------|------|
| **Python-Markdown** `==3.3.4` | 服务端 Markdown → HTML 渲染 | `config/requirements.txt` |
| **marked.js** (v0.3.x) | 客户端 Markdown 解析引擎 | `static/lib/marked/marked.js` |
| **marked-ext.js** | 自定义 Renderer 扩展（任务列表、LaTeX、CSV、TOC 等） | `static/js/marked-ext.js` |
| **TextParser** (自研) | Python-Markdown 不可用时的回退解析器 | `xutils/text_parser.py` |
| **KaTeX** | LaTeX 数学公式客户端渲染（CDN 按需加载） | `common/script/load_markdown.html` |
| **Highlight.js** | 代码高亮客户端渲染（CDN 按需加载） | `common/script/load_markdown.html` |
| **CodeMirror** | 桌面端 Markdown 编辑器 | `static/lib/codemirror/mode/markdown.js` |

---

## 2. 数据模型

- **笔记类型**：`type = "md"`（显示名称："markdown文档"）
- **别名映射**：`document`、`sticky`、`plan` 均映射到 `md`
- **存储字段**：
  - `NoteDO.content` — 原始 Markdown 文本（核心字段）
  - `NoteDO.data` — 已处理的 HTML（用于 html/post 类型）
- **判断方法**：`NoteIndexDO.is_markdown` → `self.type == "md"`

详见 `note/models.py`、`note/constant.py`。

---

## 3. 数据流：编辑 → 保存

```
用户编辑（浏览器）
  ├─ 桌面端：markdown_edit.html (CodeMirror, mode: text/x-markdown)
  │     ├─ 自动草稿：每 500ms POST /note/draft
  │     ├─ 实时预览：每 200ms marked.parseAndRender()
  │     └─ 工具栏：加粗、代码块、表格格式化等
  │
  └─ 移动端：markdown_edit.mobile.html (textarea + 键盘行)
        └─ AJAX POST /note/save

保存到服务端
  └─ SaveAjaxHandler.do_post()  →  note_edit.py:422
        ├─ 校验版本号 (NoteDO.version)
        ├─ note.content = raw markdown
        ├─ update_and_notify()
        │     ├─ 加编辑锁检查
        │     ├─ add_history() 记录历史版本
        │     └─ update_note() → _full_db.put_by_id()
        └─ fire "note.updated" / "note.update" 事件
```

关键文件：`note/note_edit.py`、`note/dao_base.py`、`note/dao_edit.py`。

---

## 4. 数据流：查看 → 渲染

### 4.1 路由分发

```
ViewHandler.GET() → VIEW_FUNC_DICT["md"] = view_or_edit_md_func()
  ├─ op=view  → markdown.html 模板（只读视图）
  └─ op=edit  → markdown_edit.html / markdown_edit.mobile.html（编辑视图）
```

路由表（`note_view.py:607-621`）：

| URL | Handler | 用途 |
|-----|---------|------|
| `/note/(edit\|view)` | `ViewHandler` | 编辑/查看页 |
| `/note/(\d+)` | `ViewByIdHandler` | 按 ID 查看 |
| `/note/view/([\w\-]+)` | `ViewByIdHandler` | 按 token 查看 |
| `/note/view/public` | `ViewPublicHandler` | 公开查看 |
| `/note/print` | `PrintHandler` | 打印视图 |
| `/note/preview_popup` | `PreviewPopupHandler` | 弹窗预览 |
| `/file/markdown` | `ViewHandler` | 别名路由 |

### 4.2 客户端渲染（主要路径）

```
markdown.html 页面加载
  ├─ load_markdown.html 按需加载 Highlight.js / KaTeX
  ├─ textarea 隐藏域存放原始 Markdown（{{!markdown_content}}）
  └─ marked.parseAndRender(input, "#markdown-output-div", options)
        │
        ├─ preHandleText()      // 将 \(...\)、\[...\]、$$...$$ 转为 <latex> 标签
        ├─ preHandleBlock()     // 处理块级 LaTeX
        │
        ├─ marked.parse(text)   // 进入自定义 Renderer
        │     ├─ heading  → 添加 id、class="marked-heading"、记录 TOC
        │     ├─ listitem → 解析 [ ]/[x] 生成可点击 checkbox
        │     ├─ paragraph→ 处理段落内 checkbox
        │     ├─ code     → 高亮分发 (CSV→表格, latex→KaTeX, 其他→hljs)
        │     ├─ codespan → <code class="marked-codespan">
        │     ├─ strong   → <strong class="marked-strong"> 搜索链接
        │     ├─ image    → 包裹 <p class="marked-img"> + x-photo 类
        │     ├─ table    → class="table marked-table"
        │     ├─ link     → target="_blank" / data-link-type
        │     ├─ html     → 过滤 <script>，<latex>→KaTeX
        │     └─ text     → 原样传递（支持 LaTeX 展开后渲染）
        │
        └─ afterRender()
              ├─ 更新 hash 链接
              ├─ _updateLatex() → KaTeX.render()
              └─ 表格宽度自适应
```

### 4.3 服务端渲染（预览弹窗、RSS 等）

```
PreviewPopupHandler  →  note_view.py:576
  └─ markdown_util.render_html(content)
        ├─ Python-Markdown (markdown.markdown)  // 首选
        └─ TextParser.render_html()              // 回退
```

### 4.4 目录（TOC）生成

- `MarkedContents` 类（`marked-ext.js:21-139`）：从 heading 收集生成嵌套 `<ul>`
- 在 `marked.parse()` 重写中：收集 headings → 生成 TOC HTML → **前置**拼接到渲染结果前
- 编辑器侧边栏：`markdown_edit_sidebar.html` + `MarkdownHeading`（`editor.js:343-470`）解析行号

---

## 5. 编辑器功能

### 桌面端（markdown_edit.html）

| 特性 | 实现 |
|------|------|
| 编辑器引擎 | CodeMirror + `mode: text/x-markdown` |
| 实时预览 | 200ms 防抖调用 `marked.parseAndRender()` |
| 自动草稿 | 500ms 防抖 POST `/note/draft` |
| 工具栏 | 加粗、代码块、删除线、表格格式化 |
| 预览开关 | 分栏模式 / 纯编辑模式切换 |
| 侧栏 TOC | `MarkdownHeading` 解析 `#` 标题，点击跳转行号 |

### 移动端（markdown_edit.mobile.html）

- 原生 textarea（无 CodeMirror）
- 键盘行：`#`、`##`、`*`、`-`、`[`、`]`、`!`、`` ` ``、代码块、Tab、箭头
- 自动调整 textarea 高度

---

## 6. 特殊功能

### 6.1 任务列表（Checkbox）

- 将 `[]`、`[x]`、`[ ]` 转为可点击的 `<input type="checkbox">`
- 点击后 AJAX 更新 Markdown 原文中的 `[ ]` → `[x]` 并保存
- 实现：`marked-ext.js:372-436`、`markdown.html:143-180`

### 6.2 LaTeX / KaTeX 数学公式

- **检测**：`markdown_util.has_latex()` 匹配 `\\(...\\)`、`\\[...\\]`、`` ```latex `` 等
- **加载**：`load_markdown.html` 根据 `markdown_content` 变量条件加载 KaTeX CSS+JS（CDN）
- **渲染**：
  - `preHandleText()` 将 `\(...\)` → `<latex>...</latex>`
  - `myRenderer.code` 处理 ` ```latex ` 代码块 → `katexRender()`
  - `_updateLatex()` 遍历 `<latex>` 元素调用 `katex.render()`

### 6.3 CSV 代码块渲染

- ` ```csv` / ` ```excel ` → `highlightCsv()` 渲染为 `<table class="csv-table">`
- 支持 `|` 分隔多种字段格式
- 支持双击单元格修改（`markdown.html:92-141`）

### 6.4 目录（TOC）

- 读取页面中所有 heading 自动生成
- 支持配置：`markedConfig.showMenu` 控制是否显示
- 可追加"事件时间线"和"评论"链接到 TOC 末尾

### 6.5 外部图片缓存

- `MarkdownImageParser`（`html_importer.py:269-398`）：解析 `![...](url)`，下载到本地
- 使用 `FsMapDao` 缓存，避免重复下载

---

## 7. 样式

| 文件 | 说明 |
|------|------|
| `static/css/base/common-markdown.css`（160行） | `.marked-heading`、`.marked-img`、`.marked-contents`、`.marked-code`、`.marked-codespan`、`.marked-strong`、`.xnote-todo/done`、`.code-line/container/header` |
| 构建系统纳入 | `xnote_code_builder.py:99` |

---

## 8. 用户配置

```
show_md_preview = true    // config/user/user_config.default.properties
```
- 控制桌面端编辑器是否自动开启预览分栏
- 类型：`UserConfigItem("show_md_preview", "Markdown预览")`

---

## 9. 测试

| 测试 | 文件位置 |
|------|----------|
| Markdown 预览接口 | `tests/test_app.py:303` |
| 创建 md 类型笔记 | `tests/test_note.py:253` |
| Markdown 图片解析器 | `tests/test_note.py:620` |

---

## 10. 完整文件清单

| 分类 | 文件 |
|------|------|
| 服务端工具 | `xutils/markdown_util.py` |
| 回退解析器 | `xutils/text_parser.py` |
| 客户端库 | `static/lib/marked/marked.js` |
| 客户端扩展 | `static/js/marked-ext.js` |
| CodeMirror 模式 | `static/lib/codemirror/mode/markdown.js` |
| 编辑器 JS | `static/js/editor.js` |
| 样式 | `static/css/base/common-markdown.css` |
| 视图模板 | `note/component/editor/markdown.html` |
| 桌面编辑器 | `note/component/editor/markdown_edit.html` |
| 移动编辑器 | `note/component/editor/markdown_edit.mobile.html` |
| 编辑器侧栏 | `note/component/sidebar/markdown_edit_sidebar.html` |
| 脚本加载器 | `common/script/load_markdown.html` |
| 打印模板 | `note/page/print.html` |
| 代码预览 | `code/page/preview.html` |
| 模型 | `note/models.py` |
| 常量 | `note/constant.py` |
| 视图 Handler | `note/note_view.py` |
| 编辑 Handler | `note/note_edit.py` |
| DAO | `note/dao_base.py`、`note/dao_edit.py` |
| 图片解析 | `note/html_importer.py` |
| Meta 配置 | `note/note_meta_config.py` |
| 代码预览 Handler | `code/preview.py` |
| 用户配置 | `core/xnote_user_config.py` |
| 构建系统 | `core/xnote_code_builder.py` |
| 系统信息 | `system/system_info.py` |
| 测试 | `tests/test_app.py`、`tests/test_note.py` |
