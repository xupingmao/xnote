## 系统架构

### 目录结构
```
xnote
|-- lib/            # 第三方类库，程序启动时添加到sys.path中
|-- static/         # 静态文件
|-- handlers/       # http请求处理器目录，功能实现大部分在这里
|   |-- system/     # 系统功能目录
|   |-- note/       # 资料功能目录
|   |-- tools/      # 工具目录
|   |-- api/        # 系统接口，返回JSON格式，供页面、定时任务、搜索调用
|   |-- ...         # 其他目录
|-- tests/          # 测试用例
|-- xutils/         # 工具类集合
|-- app.py          # 程序入口
|-- xconfig.py      # 程序配置
|-- xmanager.py     # handlers管理器，负责模块加载，注册URL，以及定时任务触发
|-- xauth.py        # 权限控制
|-- xtables.py      # 数据库表结构，自动建表
|-- xtemplate.py    # view渲染接口   
|-- autoreload.py   # 监控文件变更自动reload，主要用于调试，生产环境可以关闭

```

### 层次架构

![架构图](https://gitee.com/xupingmao/xnote/raw/master/screenshots/architecture.png)



## 开发框架/软件库

具体版本见`requirements.txt`

- webpy(修改版，xnote内置)
- tornado template(修改版，xnote内置)
- sqlite3 (Python自带文件型数据库)
- psutil(可选，采集系统运行数据)
- comtypes(可选，用于调用微软语音API)

## 前端

- jquery
- marked(markdown解析器)
- qrcode 二维码生成器
- csv.js
- jsdiff
- codemirror

### 开发新模块

在handlers目录下添加python程序，比如test.py

```py
class handler:    
    def GET(self):
        return "success"
# 如果配置了xurls全局变量，xnote会注册指定的url pattern否则按照相对handlers的路径注册
xurls = (
    r"/test", handler
)
# 启动xnote，访问浏览器localhost:1234/test就会看到success
```
