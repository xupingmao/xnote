# xnote

[![Build Status](https://travis-ci.org/xupingmao/xnote.svg?branch=master)](https://travis-ci.org/xupingmao/xnote)

xnote是一个基于Python的PIM(Personal Information Management)系统，提供内容管理系统以及常用的工具集成环境

作为一名程序猿，对我来说，有两件事情让我觉得非常重要，一是知识经验的积累，二是集成的工具，前者帮我出谋划策，而后者则能为我攻城略地。现在前者已经得到了很好的改善，有很多好用的工具可以用来记笔记，管理文档。对于后者，我们确实有很多很好的工具，但是也往往不能很好的满足一些特殊的开发需求，所以很多程序员都是使用脚本语言自己临时写小工具。除此之外，管理大量的软件也是个麻烦事，软件之间互不联通，执行一些批量操作人工成本不小。所以我准备做一款工具来满足自己的需求，它应该有如下特征

- 资料库管理功能(笔记功能)
- 集成开发工具，并且很容易扩展和查找，而且修改之后立即生效，最好可以动态开启和关闭(开发工具集成)
- 强化搜索功能，部分功能直接可以通过搜索框使用(搜索优化，最终目标是输入输出优化)
- 可以跨平台，既可以在云端使用(使用webapp的模式)，也能运行在本地作为系统增强软件
 
笔记的目的是管理知识，xnote最终目标也是管理个人生活工作中的数据和知识.

PS：个人非常喜欢插件式架构软件（比如上古神器Emacs，当代豪杰sublime text, Idea Intellij等等)，他们拥有无限扩展的可能。xnote也会朝着可自由扩展方向前进

注意：本项目主要目标人群是个人，目前多用户场景考虑不多，并发支持有限

-----
## 项目地址
- [github](https://github.com/xupingmao/xnote)
- [码云](https://git.oschina.net/xupingmao/xnote)

## Python版本

- Python 3.x
- Python 2.7

## 配置运行
- 安装依赖的软件包```python -m pip install -r requirements.txt```
- 无需额外配置，初始化的管理员账号是admin/123456
- 启动服务器`python app.py`, 默认1234端口, 浏览器打开http://localhost:1234/ 即可
- 本项目可以直接运行在新浪云应用SAE上面，还没注册SAE的同学可以用下面注册码注册（求云豆~) http://t.cn/RX2al0O 

## 功能结构

### 文档管理
- Markdown编辑器
- 文档标签
- 搜索
- 分享，可以把资料生成一个临时链接分享给朋友

### 搜索
- 笔记搜索
- 工具搜索，搜索`handlers/tools/`目录下的工具
- 翻译（由于版权问题，数据库未上传，可以自己使用相关数据库修改翻译代码）
- 计算简单的数学公式
- 添加语音提醒，比如 {30|数字}分钟后提醒我{读书},那么30分钟后就会听到电脑姐姐的温馨提醒了^_^


### 集成的工具
- 文件管理器(管理员权限)
 - 文件列表
 - 文件上传下载
 - 代码搜索
 - 代码行统计
- Python文档(pydoc)
- 代码模板
- 文本比较工具(jsdiff)
- 编解码工具(base64,16进制等等)
- 二维码生成器(barcode)
- 语音播报（基于操作系统自带语音助手）
- 天气信息抓取(中国天气网数据)
- 脚本管理器


### 定时任务
- 通过配置页面设置要调用的URL和时间匹配规则即可
- 定时任务按照`{protocol}://{URL}`规则配置，protocol缺省值为local,也就是xnote自身的handler，有效的protocol如下
 - `http`, `https` 外部的网络请求
 - `script` 执行位于`$DATA/scripts`目录下的自定义Python脚本

![定时任务配置](https://git.oschina.net/xupingmao/xnote/raw/master/static/image/%E5%AE%9A%E6%97%B6%E4%BB%BB%E5%8A%A1%E9%85%8D%E7%BD%AE.PNG)

- `handlers/tools`目录下是开发工具，可以通过搜索功能定位
- `$DATA_DIR/scripts/`目录下是系统脚本,直接与操作系统交互

### 其他特性
- debug模式下自动侦测文件修改并重新加载
- 支持文件下载断点续传,发生网络故障后不用重新下载
- 使用响应式布局
- 用户权限，通过Python的装饰器语法，比较方便修改和扩展(见xauth.login_required)
- 数据库结构自动更新(xtables.py)
- 图标，是的我自己做了一个很丑的图标，寓意天圆地方

### 开发框架/软件库

具体版本见`requirements.txt`

- webpy(修改版，xnote内置)
- tornado template(修改版，xnote内置)
- sqlite3 (Python自带文件型数据库，不支持多线程操作)
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
|-- lib/            # 第三方类库，已经添加到sys.path中
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

![架构图](https://git.oschina.net/xupingmao/xnote/raw/master/static/image/architecture.svg)

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


## 协议

- MIT

