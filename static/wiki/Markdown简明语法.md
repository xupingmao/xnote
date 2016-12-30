markdown是一种流行的简洁强大的网页编辑格式，本文档旨在简单介绍markdown的功能和用法，作为一个快速入门的参考

## 目录

- [标题](#标题)
- [段落](#段落)
- [图片](#图片)
- [链接](#链接)
- [表格](#表格)
- [代码](#代码)
- [任务列表](#任务列表)

## 标题

```
# 一级标题
## 二级标题
### 三级标题
...
以此类推
```

# 一级标题
## 二级标题
### 三级标题

---
## 段落

```
这是一个段落
，还是第一个段落

空白行之后是第二个段落

```

这是一个段落
，还是第一个段落

空白行之后是第二个段落


## 图片

```
![简介](Tulips.jpg)
```
![简介](Tulips.jpg)

## 链接

```
[百度](http://www.baidu.com)

```
[百度](http://www.baidu.com)


'#' + 标题名，本文件中跳转比如

```
[目录](#目录)
```

[目录](#目录)

---
## 表格

### 简单表格

```
dog | bird | cat
----|------|----
foo | foo  | foo
bar | bar  | bar
baz | baz  | baz
```

效果

dog | bird | cat
----|------|----
foo | foo  | foo
bar | bar  | bar
baz | baz  | baz

### 表格对齐

```
| Tables        | Are           | Cool  |
| ------------- |:-------------:| -----:|
| col 3 is      | right-aligned | $1600 |
| col 2 is      | centered      |   $12 |
| zebra stripes | are neat      |    $1 |
```

效果

| Tables        | Are           | Cool  |
| ------------- |:-------------:| -----:|
| col 3 is      | right-aligned | $1600 |
| col 2 is      | centered      |   $12 |
| zebra stripes | are neat      |    $1 |


## 任务列表

*marked原生不支持，已经通过扩展支持,github支持*

```
- [x] 已完成
- [] 未完成
```

效果

- [x] 已完成
- [] 未完成