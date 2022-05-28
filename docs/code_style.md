# 编码规范

这个文档主要描述xnote的编码规范，基于 [PEP8](https://www.python.org/dev/peps/pep-0008/) 的基础进行补充

其他命名规范
- [CSS命名规范](./code_style_css.md)

# 1. 变量命名

全局变量全大写+下划线命名

> 示例如下

```py
MY_GLOBAL_VAR = 1
```

局部变量全小写+下划线命名

> 示例如下

```py
my_local_var = 1
# 没有歧义的也可以不加下划线
filename = "myfile.txt" 
```

# 2. 包命名

- 小写字母+下划线，名词短语结构，示例: 
    - `core` 简单的包
    - `my_package` 带下划线的包名
    - `simplepackage` 没有歧义的也可以不加下划线

> 示例如下

```py
core # 简单包名
simplepackage # 无歧义的包名
my_package # 带下划线的包名
```

# 3. 类命名

- 首字母大写驼峰命名，示例: `MyClass`
- 领域+性质(类型)，示例:
    - NoteHandlerBase 笔记处理器的基类
    - NoteListHandler 笔记列表处理器
    - TaskManager 任务管理器
    - NoteTaskManager 笔记任务管理器
- 分层命名规则：
    - 视图层（handlers）: 具体的功能，有状态，包括API和页面，处理业务逻辑
    - 核心层（core）: 基于功能抽象出来的通用能力，适用于WEB应用，有状态，只处理功能逻辑，不感知业务逻辑
    - 基础层（xutils/lib）: 非常基础并且通用的能力，适用于全部领域，基本无状态

## 3.1 manager和service的区别

- service提供具体的服务（外部使用），manager（内部使用）是service下面一层，为service提供通用服务

# 4. 函数命名

- 普通函数，小写+下划线，结构为（[前缀]+动名词结构）示例: 
    - `my_func`
    - `get_some_value`
    - `convert_a_to_b`
- 装饰器，小写+下划线+`deco`，示例: 
    - `my_log_deco`

说明：由于Python本身有类和模块的结构，函数不建议用前缀，直接用`模块.函数`的方式。

# 5. 近义词区分

- type和category
    - type是偏向于客观边界比较清晰的分类，比如动植物的类型、建筑材料类型、数据结构类型等等
    - category是偏向于主观的分类，比如文章分类、活动类型等等

# 6. 模块内部的命名

- `handlers/note` note模块的根目录
- `handlers/note/page/` 静态页面目录
- `handlers/note/ajax/` ajax页面目录
- `handlers/note/component/` 页面的组件
- `handlers/note/component/css` CSS组件
- `handlers/note/component/script` JS脚本组件
- `handlers/note/*.py` 后台处理程序

> 示例

```text
handlers/note/
|-- page
|   |-- note_index.html
|   `-- note_create.html
|-- ajax
|   |-- note_option_dialog.html
|   `-- note_select_dialog.html
|-- component
|   |-- css
|   |   |-- layout_css.html
|   |   `-- header_css.html
|   |-- script
|   |   |-- option_script.html
|   |   `-- search_script.html
|   `-- header.html
|-- note_dao.py   # 数据访问对象
|-- note_page.py  # 页面的controller
`-- note_ajax.py  # AJAX请求的controller
```
