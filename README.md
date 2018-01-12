# Xnote

[![Build Status](https://travis-ci.org/xupingmao/xnote.svg?branch=master)](https://travis-ci.org/xupingmao/xnote)
[![Coverage Status](https://coveralls.io/repos/github/xupingmao/xnote/badge.svg?branch=master)](https://coveralls.io/github/xupingmao/xnote?branch=master)

xnote是一款致力于提升生活和工作的幸福感的工具，通过将知识库和工具有机结合起来，提供简单好用的个人助理服务。它有如下特点

- 知识库管理，维护文章、日志、个人词库以及文件数据
- 可扩展，通过脚本扩展系统功能，监听系统事件完成自定义功能
- 智能搜索，支持搜索知识库、文件系统、工具等等，支持简单的语义指令
- BS架构、跨平台，既可以在云端部署，也能运行在本地作为系统增强软件


PS：目前本项目主要目标人群是个人，提供有限的多用户支持

-----
## 项目地址
- [github](https://github.com/xupingmao/xnote)
- [码云](https://gitee.com/xupingmao/xnote)

### 关于版本

- master版本是开发版本，可以体验最新功能特性，考虑稳定性可以下载tag版本。
- 目前的大版本是1.0版本，小版本暂时3个月左右迭代一次，质量主要通过自动化测试保证，小版本开发完之后，如果运行一段时间没有明显BUG我会创建一个新的Tag分支。
- 升级过程中尽量向前兼容，大部分的数据库结构变更可以自动执行，不兼容的地方将会在Release Log中加以说明。

## Python版本

- Python 3.x
- Python 2.7
- Jython (无sqlite)

## 配置运行
- 安装依赖的软件包```python -m pip install -r requirements.txt```
- 无需额外配置，初始化的管理员账号是admin/123456
- 启动服务器`python app.py`, 默认1234端口, 浏览器打开http://localhost:1234/ 即可
- 本项目可以直接运行在新浪云应用SAE上面

### 启动参数
- `--data {data_path}` 指定数据存储的data目录，比如`python app.py --data D:/data`
- `--port 1234`启动端口号，注意优先使用环境变量{PORT}设置的端口号，这是为了自适应云服务容器的端口
- `--ringtone yes`开启启动语音提醒
- `--delay 60` 延迟启动，单位是秒，这个主要是为了避免重启的定时任务重复执行
- `--useUrlencode yes`针对只支持ASCII编码的文件系统开启urlencode转换非ASCII码字符
- `--initScript {script_name}` 启动时运行指定脚本完成自定义初始化操作

### 数据库升级

如果启动失败，报数据库字段错误、或者是启动成功但是丢失了资料的日期信息，那么可能是安装了早期版本导致的，需要对数据库进行一次手动升级，由于sqlite不支持字段重命名，所以会略微麻烦一些。

升级工作主要是三步，如下所示，需要说明的是备份可以登陆到服务器使用sqlite安装程序，也可以通过关键字`sql`搜索出xnote自带的工具操作

- 备份`file`表,

```
alter table file rename to file_20171124;
```

- 创建新的`file`表，这一步可以通过重新启动xnote来自动创建
- 把备份数据迁移到新的`file`表中

```
insert into file ( id, name, content, data, size, version, type, 
parent_id, related, ctime, mtime, atime, visited_cnt, is_deleted, is_public, is_marked,
creator, modifier, groups, priority) 
select id, name, content, data, size, version, type, 
parent_id, related, sctime, smtime, satime, visited_cnt, is_deleted, is_public, is_marked,
creator, modifier, groups, priority from file_20171124;

```

## 功能结构

### 知识库
- Markdown编辑器、可视化编辑器
- 文档分组、标签
- 文档分享
- 搜索


### 日程管理
- 任务清单功能，类似于微博的形式，可以写文字或者上传图片文件等、目前有进行中和完成两个状态
- 日历，日程提醒功能考虑中

### 搜索

搜索提供数据和很多程序的入口，并且支持一些语义化的命令

- [x] 知识库搜索
- [] 词典检索
- [x] 书籍搜索，搜索`$DATA/books/`目录下的书籍
- [x] 工具搜索，搜索`handlers/tools/`目录下的工具
- [x] 计算简单的数学公式
- [x] 支持一些语义化的功能，比如添加语音提醒，输入 `{30|数字}分钟后提醒我{读书}`,那么30分钟后就会听到电脑姐姐的温馨提醒了^\_^


### 文件管理器
- 需要管理员权限
- 文件列表
- 文件上传下载
- 代码搜索
- 代码行统计

### 定时任务
- 通过配置页面设置执行的脚本和时间匹配规则即可
- 可选的任务包括`handlers/api`目录下的系统API以及`scripts`目录下的自定义脚本
- 自定义脚本支持Python脚本和面向操作系统的原生脚本，包括类Unix的shell脚本和Windows的BAT脚本

 
### 其他工具
- Python文档(pydoc)
- 代码模板
- 文本比较工具(jsdiff)
- 编解码工具(base64,16进制等等)
- 二维码生成器(barcode)
- 语音播报（基于操作系统自带语音助手）
- 天气信息抓取(中国天气网数据)
- 脚本管理器

### 其他特性
- debug模式下自动侦测文件修改并重新加载
- 支持文件下载断点续传,发生网络故障后不用重新下载
- 使用响应式布局，尽量保证PC、移动平台体验一致
- 用户权限，通过Python的装饰器语法，比较方便修改和扩展(见xauth.login\_required)
- 数据库结构自动更新(xtables.py)
- 支持纯ASCII码文件系统（上传文件名会经过urlencode转码）


### 开发框架/软件库

具体版本见`requirements.txt`

- webpy(修改版，xnote内置)
- tornado template(修改版，xnote内置)
- sqlite3 (Python自带文件型数据库)
- psutil(可选，采集系统运行数据)
- comtypes(可选，用于调用微软语音API)

### 前端

- jquery
- marked(markdown解析器)
- qrcode 二维码生成器
- csv.js
- jsdiff
- codemirror

## 系统架构

### 目录结构
```
xnote
|-- lib/            # 第三方类库，程序启动时添加到sys.path中
|-- static/         # 静态文件
|-- handlers/       # http请求处理器目录，功能实现大部分在这里
|   |-- system/     # 系统功能目录
|   |-- file/       # 资料目录
|   |-- tools/      # 工具目录
|   |-- api/        # 系统接口，返回JSON格式，供页面、定时任务、搜索调用
|   |-- ...         # 其他目录
|-- tests/          # 测试用例
|-- app.py          # 程序入口
|-- xconfig.py      # 程序配置
|-- xmanager.py     # handlers管理器，负责模块加载，注册URL，以及定时任务触发
|-- xauth.py        # 权限控制
|-- xtables.py      # 数据库表结构，自动建表
|-- xtemplate.py    # view渲染接口
|-- xutils.py       # 工具类统一入口
|-- autoreload.py   # 监控文件变更自动reload，主要用于调试，生产环境可以关闭

```

### 层次架构

![架构图](https://gitee.com/xupingmao/xnote/raw/master/screenshots/architecture.png)

### 扩展

在handlers目录下添加python程序，比如test.py

```py
class handler:    
    def GET(self):
        return "success"
# 如果配置了xurls全局变量，xnote会注册指定的url pattern否则按照相对handlers的路径注册
xurls = ("/test", handler)
# 启动xnote，访问浏览器localhost:1234/test就会看到success
```

## 运行截图

知识库

![知识库](https://git.oschina.net/xupingmao/xnote/raw/master/screenshots/xnote_v1.2_editor.PNG)

任务清单

![清单](https://git.oschina.net/xupingmao/xnote/raw/master/screenshots/xnote_v1.2_list.PNG)

搜索

![截图03](https://git.oschina.net/xupingmao/xnote/raw/master/screenshots/xnote_v1.2_search.png)

定时任务

![定时任务配置](https://git.oschina.net/xupingmao/xnote/raw/master/screenshots/task_web.PNG)


## 协议

- GPL

