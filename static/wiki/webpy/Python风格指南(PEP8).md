## 宗旨

- Readability counts

# 变量命名
下划线风格
```
# 普通变量
this_is_a_var = 10

# 双下划线开始一般是系统变量
__name__ = "main"

# 匿名全局变量,不会被其他包导入
_global_var = 1

# 常量，全大写
MAX_RETRY = 100

```

# 方法命名
下划线
```
def my_func():
    ...
```

# 类命名
驼峰，首字母大写
```
class MyClass:
    # 类匿名变量
    __inner_name = "test"
    # 公开的变量
    name = "MyClass"
    ...

```


## 引用

- https://www.python.org/dev/peps/pep-0008/