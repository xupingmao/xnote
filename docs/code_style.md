# 编码规范

这个文档主要描述xnote的编码规范，基于 [PEP8](https://www.python.org/dev/peps/pep-0008/) 的基础进行补充

# 1. 变量命名

- 全局变量全大写+下划线命名，示例:
    - `MY_GLOBAL_VAR`
- 局部变量全小写+下划线命名，示例:
    - `my_local_var`
    - `filename` 没有歧义的也可以不加下划线

# 2. 包命名
- 小写字母+下划线，示例: 
    - `core` 简单的包
    - `my_package` 带下划线的包名
    - `simplepackage` 没有歧义的也可以不加下划线


# 3. 类命名

- 首字母大写驼峰命名，示例: `MyClass`
- 领域+性质(类型)，示例:
    - NoteHandlerBase 笔记处理器的基类
    - NoteListHandler 笔记列表处理器
    - TaskManager 任务管理器
    - NoteTaskManager 笔记任务管理器
- 分层命名规则：
    - 视图层（handlers）: 具体的功能，有状态，包括API和页面
    - 核心层（core）: 基于功能抽象出来的通用能力，适用于WEB应用，有状态
    - 基础层（xutils/lib）: 非常基础并且通用的能力，适用于全部领域，基本无状态

## 3.1 manager和service的区别

- service提供具体的服务（外部使用），manager是service下面一层，为service提供通用服务（内部使用）

# 4. 函数命名

- 普通函数，小写+下划线，示例: 
    - `my_func`
- 装饰器，小写+下划线+`deco`，示例: 
    - `my_log_deco`

# 5. 近义词区分

- type和category
    - type是偏向于客观边界比较清晰的分类，比如动植物的类型、建筑材料类型、数据结构类型等等
    - category是偏向于主观的分类，比如文章分类、活动类型等等
