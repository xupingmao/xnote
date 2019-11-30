# Xnote

[![Build Status](https://travis-ci.org/xupingmao/xnote.svg?branch=master)](https://travis-ci.org/xupingmao/xnote)
[![Coverage Status](https://coveralls.io/repos/github/xupingmao/xnote/badge.svg?branch=master)](https://coveralls.io/github/xupingmao/xnote?branch=master)

xnote是一款面向个人的轻量级笔记系统，提供多种维度的数据管理功能。它主要有如下特性

- 拥有丰富的数据管理能力，支持多种笔记格式以及文件管理功能
- 自带工具箱，默认提供了大量常用的工具
- 提供扩展能力，用户可以编写各种插件满足自己的需求
- 跨平台，支持Windows、Mac、Linux三大平台，可以在云服务上部署，也可以在本地运行
- 多用户支持

![主页](https://git.oschina.net/xupingmao/xnote/raw/master/screenshots/xnote_v2.4_home2.png)

-----
## 项目地址
- [github](https://github.com/xupingmao/xnote)
- [码云](https://gitee.com/xupingmao/xnote)


## 安装运行
- 安装python（支持Python2、3，建议Python3）
- 安装依赖的软件包
    - Mac/Linux执行 ```python -m pip install -r requirements.txt```
    - Windows执行 `python -m pip install -r requirements.win.txt`
- 启动服务器`python app.py`, 默认1234端口, 浏览器打开http://localhost:1234/ 无需额外配置，初始化的管理员账号是admin/123456
- 可以直接部署在新浪云应用SAE上面
- 如果安装老版本后更新启动失败参考 [数据库迁移](./docs/db_migrate.md)

### 启动参数
- `--data {data_path}` 指定数据存储的data目录，比如`python app.py --data D:/data`
- `--port 1234`启动端口号，注意优先使用环境变量{PORT}设置的端口号，这是为了自适应云服务容器的端口
- `--useUrlencode yes`针对只支持ASCII编码的文件系统开启urlencode转换非ASCII码字符
- `--minthreads {number}` web请求处理线程数


## 主要功能

### 笔记管理
- 支持多种格式：markdown/富文本/表格/相册
- 组织功能：提供文件夹和标签两种方式来组织文档
- 搜索功能：按标题和内容搜索
- 分享功能：可以开放为未登录用户查看
- 优先级管理：置顶、归档功能
- 安全功能：修改历史
- 其他文档工具

### 提醒管理
- 可以快速写文字提醒或者上传图片、文件等
- 提醒有关注、挂起、完成三个状态，基本满足日常工作需求
- 支持搜索和hashtag
- 日历功能，暂时比较简单

### 文件管理
- 列表、网格等多种视图模式
- 文件上传、下载、新建、删除、重命名、剪切、粘贴等操作
- 文本编辑器
- 文本内容搜索
- 代码行统计工具
- WebShell工具
- 支持命令扩展
- 文件下载支持断点续传，支持超大文件上传（测试过1G文件）
- 支持ASCII码文件系统，通过urlencode对文件名转码

### 工具箱
- Python文档(pydoc)
- 文本处理(文本对比、代码生成、密码生成)
- 编解码工具(base64、md5、进制转换、等等)
- 条形码、二维码生成器
- 图像处理（合并、拆分、灰度转换）
- 提供扩展能力

## 系统扩展

由于每个人的需求不同，单一系统很难满足，开发者可以根据自己需要编写插件来扩展系统的功能。具体可以参考文档 [插件扩展](./docs/plugins.md)。

具体特性如下

- 插件中可以监听系统消息，包括笔记、提醒、文件、时间、系统五种类型的消息
- 插件可以通过`category`属性设置分类，显示在笔记、文件、系统等功能的选项入口中
- 可以通过模板创建插件

### 相关文档
- [更新日志](./docs/changelog.md)
- [插件扩展](./docs/plugins.md)
- [搜索扩展](./docs/search_extension.md)
- [命令扩展](./docs/commands.md)
- [系统架构](./docs/architecture.md)

## 协议

- GPL

