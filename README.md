# xnote

[![Build Status](https://travis-ci.org/xupingmao/xnote.svg?branch=master)](https://travis-ci.org/xupingmao/xnote)

xnote是一个基于webapp的笔记系统，提供类似于wiki的资料管理系统以及常用的工具集成环境(主要是开发工具)

作为一名程序猿，对我来说，有两件事情让我觉得非常重要，一是知识经验的积累，而是集成的工具，前者帮我出谋划策，而后者则能为我攻城略地。现在前者已经得到了很好的改善，有很多好用的工具可以用来记笔记，管理文档。但是后者我觉得还是比较尴尬的，有一些网站集成了一些工具供我们使用，但是也往往不能很好的满足开发需求，一方面受限于网络安全不能操作本地文件，另一方面则是有的需求确实太独特无法推广成软件来使用。管理大量的软件也是个麻烦事，而且有的软件启动缓慢，功能冗余。所以我准备做一款工具来满足自己的需求，它应该有如下特征

- 提供资料编辑搜索功能(笔记功能)
- 集成开发工具，并且很容易扩展和查找，而且修改之后立即生效，最好可以动态开启和关闭(开发工具集成)
- 有些功能最好直接可以通过搜索框使用(搜索优化，最终目标是输入输出优化)
- 不在家的时候我也想在手机上使用(使用webapp的模式)
 
笔记的目的是管理知识，xnote最终目标也是管理个人生活工作中的数据和知识.

PS：我觉得IDE是一个非常伟大的创新，大大提高了程序员编码的效率，而且插件式的架构设计也不难扩展，我一度想采用开发IDE插件的方式来完成，但是由于IDE不支持网络访问，启动缓慢，难以完全掌握等原因还是放弃了。

注意：本项目主要是个人使用，不考虑并发性能，界面设计上面也不会花太多的精力

-----
## 环境依赖

- Python 3

### 开发框架/软件库

- webpy(修改版)
- tornado template(修改版)
- sqlite3 (Python自带文件型数据库，不支持多线程操作)
- psutil(可选，采集系统运行数据)
- comtypes(可选，用于调用微软语音API)

### 前端

- jquery(当然^_^)
- marked(markdown解析器)
- qrcode 二维码生成器
- csv.js
- jsdiff
- codemirror

## 功能结构

- 自动搜索`handlers`目录下的Python文件中的handler，可以通过继承约定或者设置`xurls`属性来配置路由，下面是一个例子

```py
# 最简单的handler
class handler:    
    def GET(self):
        return "success"

xurls = ("/test", handler)
# 放在handlers目录下面，然后访问浏览器localhost:1234/test就会看到success
```

- `handlers/tasks`是定时任务, 需要在任务管理功能中增加服务地址，设置执行周期，如下图（分别是备份和系统监控的定时任务)

![定时任务配置](https://git.oschina.net/xupingmao/xnote/raw/master/static/img/%E5%AE%9A%E6%97%B6%E4%BB%BB%E5%8A%A1%E9%85%8D%E7%BD%AE.PNG)

- `handlers/tools`目录下是开发工具，可以通过搜索功能定位
- `scripts/`目录下是系统脚本,直接与操作系统交互

### 搜索
- 笔记搜索
- 工具搜索，搜索`handlers/tools/`目录下的工具
- 翻译（由于版权问题，数据库未上传）
- 计算简单的数学公式

### 集成的工具
- 可以在根目录下自行添加tools.md文件,使用admin用户登陆后可以直接在xnote上编辑
- 文件浏览器，局域网内传输数据再也不需要数据线啦(地址如localhost:1234/fs/D:/,目前仅限admin，支持一些简单的工具，比如代码内容搜索，wiki编辑)
- 编解码工具(base64,16进制等等)
- 二维码生成器(barcode)
- 文本比较工具(jsdiff)
- 代码模板(code_template)

### 其他
- debug模式下自动侦测文件修改并重新加载
- 支持文件断点续传
- 使用响应式布局（其实是偷懒）
- 用户权限，通过Python的装饰器语法，比较方便修改和扩展(见xauth.login_required)
- 数据库结构全自动更新(xtables.py)
- 图标，是的我自己做了一个很丑的图标，寓意天圆地方

## 配置运行
- config/users.ini 用户配置，管理员可以添加账户，不支持注册
- config/menu.ini 导航菜单配置，可以在系统页面编辑菜单配置
- 启动服务器`python app.py`, 默认1234端口, 浏览器打开http://localhost:1234/ 即可

## 协议

- MIT