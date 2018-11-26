# Xnote

[![Build Status](https://travis-ci.org/xupingmao/xnote.svg?branch=master)](https://travis-ci.org/xupingmao/xnote)
[![Coverage Status](https://coveralls.io/repos/github/xupingmao/xnote/badge.svg?branch=master)](https://coveralls.io/github/xupingmao/xnote?branch=master)

xnote是一款致力于提升生活和工作的幸福感的工具，通过将知识库和工具有机结合起来，提供简单好用的个人助理服务。它有如下特点

- 多元数据管理，笔记、提醒、词典以及文件数据N合一
- 工具箱，默认提供了大量常用的工具
- 可扩展，通过编写插件扩展系统功能，通过事件监听与系统深度互动，可以完成定时任务、搜索扩展、文本实时分析等功能
- 跨平台，支持Windows、Mac、Linux三大平台，可以在云服务上部署，也可以在本地运行


PS：目前本项目主要目标人群是个人，提供有限的多用户支持

![主页](https://git.oschina.net/xupingmao/xnote/raw/master/screenshots/xnote_v2.1_home.png)

-----
## 项目地址
- [github](https://github.com/xupingmao/xnote)
- [码云](https://gitee.com/xupingmao/xnote)


## 安装运行
- 安装python（支持Python2、3，建议Python3）
- 安装依赖的软件包```python -m pip install -r requirements.txt```
- 启动服务器`python app.py`, 默认1234端口, 浏览器打开http://localhost:1234/ 无需额外配置，初始化的管理员账号是admin/123456
- 可以直接部署在新浪云应用SAE上面
- 如果安装老版本后更新启动失败参考 [数据库迁移](./docs/db_migrate.md)

### 启动参数
- `--data {data_path}` 指定数据存储的data目录，比如`python app.py --data D:/data`
- `--port 1234`启动端口号，注意优先使用环境变量{PORT}设置的端口号，这是为了自适应云服务容器的端口
- `--useUrlencode yes`针对只支持ASCII编码的文件系统开启urlencode转换非ASCII码字符


## 主要功能

### 知识库
- 编辑器支持markdown和富文本两种方式，建议使用markdown
- 提供分组和标签两种方式来组织文档
- 支持文档分享，公开后文章可以被游客访问
- 支持标题和内容搜索
- 支持按用户进行权限隔离

### 提醒
- 可以快速写文字或者上传图片文件等
- 提醒有关注、挂起、完成三个状态，基本满足日常工作需求
- 提供按照用户进行权限隔离
- 日历功能，暂时比较简单

### 文件管理器
- 访问需要管理员权限
- 列表、网格等多种视图模式
- 文件上传下载、创建、删除、重命名、剪切等操作
- 文本编辑器
- 文本内容搜索
- 代码行统计
- WebShell

### 定时任务
- 通过自定义脚本，对系统功能进行扩展增强
- 通过配置页面设置执行的脚本和时间匹配规则即可
- 可选的任务包括`handlers/api`目录下的系统API以及`scripts`目录下的自定义脚本
- 自定义脚本支持Python脚本和面向操作系统的原生脚本，包括类Unix的shell脚本和Windows的BAT脚本
- 可以通过插件监听cron.hour和cron.minute事件来完成定时任务

### 插件扩展

- 搜索提供数据和很多程序的入口，并且支持一些语义化的命令，比如添加语音提醒，输入 `{30|数字}分钟后提醒我{读书}`,那么30分钟后就会听到电脑姐姐的温馨提醒了^\_^
- 自定义初始化脚本
- [插件扩展](./docs/plugins.md)
- [命令扩展](./docs/commands.md)

 
### 工具箱
- Python文档(pydoc)
- 文本处理(文本对比，代码生成，密码生成)
- 编解码工具(base64,16进制等等)
- 条形码、二维码生成器(barcode)
- 图像处理（合并、拆分、灰度化）

### 其他特性
- debug模式下自动侦测模块修改并重新加载
- 支持文件下载断点续传,发生网络故障后不用重新下载
- 使用响应式布局，尽量保证PC、移动平台体验一致
- 用户权限，通过Python的装饰器语法，比较方便修改和扩展(见xauth.login\_required)
- 数据库结构自动更新(xtables.py)
- 支持纯ASCII码文件系统（上传文件名会经过urlencode转码）
- 单元测试覆盖率50%以上
- 自定义启动脚本
- 自定义CSS

## 相关文档
- [系统架构](./docs/architecture.md)

## 协议

- GPL

