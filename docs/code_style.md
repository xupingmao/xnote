# 代码规范

这个文档主要描述xnote的开发规范

# 变量命名

- 全局变量全大写+下划线命名，示例:
    - `MY_GLOBAL_VAR`
- 局部变量全小写+下划线命名，示例:
    - `my_local_var`
    - `filename` 没有歧义的也可以不加下划线

# 包命名
- 小写字母+下划线，示例: 
    - `core` 简单的包
    - `my_package` 带下划线的包名
    - `simplepackage` 没有歧义的也可以不加下划线


# 类命名

- 首字母大写驼峰命名，示例: `MyClass`
- 领域+性质(类型)，示例:
    - NoteHandlerBase 笔记处理器的基类
    - NoteListHandler 笔记列表处理器

# 函数命名

- 普通函数，小写+下划线，示例: 
    - `my_func`
- 装饰器，小写+下划线+`deco`，示例: 
    - `my_log_deco`

# 近义词区分

- type和category
    - type是偏向于客观边界比较清晰的分类，比如动植物的类型、建筑材料类型、数据结构类型等等
    - category是偏向于主观的分类，比如文章分类、活动类型等等
