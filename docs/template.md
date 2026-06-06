# Template Engine

xnote 的模板系统分为两层：

1. **底层模板引擎** — `xutils/tornado/template.py`，Tornado 模板引擎的魔改版
2. **上层 xnote 封装** — `xnote/core/xtemplate.py`，提供统一渲染入口、设备适配、国际化等能力

---

## 底层引擎语法（xutils/tornado/template）

模板编译为 Python 字节码执行，支持任意 Python 表达式。

### 表达式

```
{{ expression }}
{{? var_name, default_value }}  {# 带默认值的变量，变量不存在时输出默认值 #}
```

默认启用 HTML 转义 (`xhtml_escape`)，可用 `{% raw %}` 输出未经转义的内容。

### 控制块

```
{% if condition %}...{% elif condition %}...{% else %}...{% end %}
{% for var in expr %}...{% end %}
{% while condition %}...{% end %}
{% try %}...{% except %}...{% else %}...{% finally %}...{% end %}
{% break %} / {% continue %}
```

### 模板继承

```
{% extends "base.html" %}
{% block name %}...{% end %}
```

### 模板包含

```
{% include "header.html" %}
```

### 其他标签

| 标签 | 说明 |
|------|------|
| `{% set x = y %}` | 设置局部变量 |
| `{% init x = y %}` | 设置变量（仅当未定义时） |
| `{% set-global x = y %}` | 设置全局变量 |
| `{% raw expr %}` | 输出原始内容（不转义） |
| `{% apply func %}...{% end %}` | 对块内输出应用函数 |
| `{% module Template(...) %}` | 渲染 UIModule |
| `{% autoescape None %}` | 禁用自动转义 |
| `{% whitespace mode %}` | 空白模式：`all` / `single` / `oneline` |
| `{% comment ... %}` | 注释（不输出） |
| `{% render expr %}` | 调用对象的 `.render()` 方法并输出 |
| `{# ... #}` | 单行注释 |
| `{{!` / `{%!` | 直接输出 `{{` / `{%` 字面量 |

### 默认命名空间

所有模板内置以下函数：

- `escape` / `xhtml_escape` — HTML 转义
- `url_escape` — URL 编码
- `json_encode` — JSON 序列化
- `squeeze` — 压缩空白
- `linkify` — 将 URL 转为链接
- `datetime` — Python datetime 模块
- `get_value(obj, namelist)` — 安全获取深层属性

---

## Xnote 渲染层（xtemplate.py）

### 核心函数

```python
from xnote.core import xtemplate

# 渲染文件模板
xtemplate.render("note/index.html", **kw)

# 渲染字符串模板（带缓存）
xtemplate.render_text("<h1>{{title}}</h1>", title="Hello")

# 预编译模板
xtemplate.compile_template("<html>{{name}}</html>", name="<string>")

# 注册内存模板
xtemplate.register_memory_template("memory:my_tpl", "<h1>{{name}}</h1>")
```

### 自动注入的模板变量

调用 `render()` 时自动注入以下变量：

| 变量 | 说明 |
|------|------|
| `math` | Python math 模块 |
| `_server_home` | 服务器根路径 |
| `_is_admin` | 当前用户是否管理员 |
| `_has_login` | 是否已登录 |
| `_user_name` | 当前用户名 |
| `_user_id` | 当前用户 ID |
| `_user_role` | 当前用户角色 |
| `_user_agent` | User-Agent 字符串 |
| `_render` | 指向 `xtemplate.render`，用于嵌套渲染 |
| `_nav_list` | 导航菜单列表 |
| `_is_mobile` | 是否移动端 |
| `_is_desktop` | 是否桌面端 |
| `Storage` | `xutils.Storage` 类 |
| `xutils` | xutils 模块 |
| `xconfig` | xconfig 模块 |
| `T` | 国际化翻译函数 |
| `_ts` | 服务器启动时间戳（前端缓存版本） |
| `_user_config` | 当前用户的配置字典 |
| `FONT_SCALE` | 字体缩放比例 |
| `HOME_PATH` | 用户首页路径 |
| `THEME` | 用户主题 |
| `HOST` | 请求的 Host |
| `search_action` / `search_placeholder` / `search_tag` | 搜索配置（按 search_type 自动注入） |
| `_cost_time` | 请求耗时 |
| `format_date` | 日期格式化函数（`dateutil.format_date`） |
| `format_time` | 时间格式化函数（`dateutil.format_time`） |
| `quote` | URL 编码（`urllib.parse.quote`） |

开发者模式下额外注入：`_debug_info`、`_dev_info`。

### 设备适配

```python
# 自动按 UA 选择模板：name.mobile.html（移动端）/ name.html（桌面端）
xtemplate.render_by_ua("note/index.html", **kw)
```

移动端渲染时自动查找 `note/index.mobile.html`，存在则使用。

### 国际化

```python
# 在模板中使用
{{ T("你好") }}

# Python API
from xnote.core.xtemplate import T
T("你好", lang="en")
```

根据当前用户 `LANG` 配置查找翻译映射，找不到则返回原文。

### 模板加载与路径解析

- 根目录：`xconfig.HANDLERS_DIR`
- `resolve_path` 特殊处理：
  - `"base"` → `{HANDLERS_DIR}/{BASE_TEMPLATE}`
  - `"wide_base"` → `{HANDLERS_DIR}/{WIDE_BASE_TEMPLATE}`
  - `"$ext/"` 前缀 → `ext_handlers_dir` 目录
  - `"$plugin/"` 前缀 → `plugins_dir` 目录
  - `"memory:"` 前缀 → 内存模板
  - `"*.str"` → 字符串模板
  - 其他 → `{HANDLERS_DIR}/{name}`
- `{% extends %}` 和 `{% include %}` 的路径强制为全局路径（不以所在模块为相对基准），避免移动模块时母版路径失效

### 内存模板

```python
# 注册
xtemplate.register_memory_template("memory:foo", "<b>{{name}}</b>")

# 在模板中使用
{% include "memory:foo" %}
```

### 渲染文本（字符串模板）

`render_text(text, template_name, **kw)`：
- 以文本的 MD5 为缓存 key，编译后缓存
- 可在插件中用于动态生成 HTML

---

## 插件模板（Plugin）

### 基类

- `BasePlugin`（别名 `BaseTextPage` / `BaseTextPlugin`）
- `BaseFormPlugin` — 带表单的插件
- `PluginBase` — 命名更优的别名

### 插件渲染流程

```python
class MyPlugin(BasePlugin):
    title = "我的插件"
    category = "system"
    require_admin = True

    def handle(self, input=""):
        self.writeline("Hello, {{name}}!")
        return self.output

    def render(self):
        self.check_access()
        output = self.handle(self.get_input())
        return xtemplate.render(self.base_template_path, **self.convert_attr_to_kw())
```

插件最终渲染的模板默认为 `plugin/base/base_plugin.html`。

### BasePlugin 属性

| 属性 | 默认值 | 说明 |
|------|--------|------|
| `title` | `"插件名称"` | 插件标题 |
| `description` | `""` | 描述 |
| `show_nav` | `True` | 显示导航 |
| `show_aside` | `False` | 显示侧边栏 |
| `CONTENT_WIDTH` | `1000` | 内容宽度 |
| `require_admin` | `True` | 需要管理员权限 |
| `require_login` | `True` | 需要登录 |
| `base_template_path` | `"plugin/base/base_plugin.html"` | 渲染模板路径 |
| `category` | `""` | 分类（note/dir/system/network） |

### 插件输出方法

- `write(text)` / `writeline(line)` / `writetext(text)` — 追加纯文本
- `writeheader(html, **kw)` — 设置 header HTML
- `writebody(html, **kw)` / `writetemplate(html, **kw)` — 渲染并追加模板
- `writehtml(html, **kw)` — 已废弃，等价于 `writetemplate`
- `write_plain_html(html)` — 追加纯 HTML（不渲染模板）
- `update_aside(html, **kw)` — 更新侧边栏
- `response_text(template, **kw)` — 返回文本响应（局部刷新场景）
- `response_ajax(template, **kw)` — 同上，已废弃别名
- `response_iter(iter)` — 返回迭代器

### 生命周期事件

- `on_action(name, context, input)` — action/confirm/prompt 按钮
- `on_command(context)` — 命令行入口
- `on_install(context)` — 安装事件
- `on_uninstall(context)` — 卸载事件
- `on_init(context)` — 初始化事件
- `on_event(event)` — 其他事件

---

## 示例

```html
{# templates/note/index.html #}
{% extends "base" %}
{% block body %}
  <h1>{{ T("笔记列表") }}</h1>
  {% for item in items %}
    <div class="row">
      <a href="{{item.url}}">{{ item.name }}</a>
      <span>{{ format_date(item.mtime) }}</span>
    </div>
  {% end %}
{% end %}
```

```python
# handler
class NoteHandler:
    def GET(self):
        items = [...]
        return xtemplate.render("note/index.html", items=items)
```
