# xnote

xnote是一个基于webapp的笔记系统，提供类似于wiki的资料管理系统以及常用的工具(主要是开发工具)

笔记的目的是管理知识，xnote最终目标也是管理个人生活工作中的数据和知识.

-----
## 环境依赖

- Python 3

## 开发框架

- webpy (修改版)
- tornado template
- cherrypy (webpy依赖的httpserver)
- sqlite3 (Python自带文件型数据库，不支持多线程操作)

## 前端

- jquery
- marked(markdown解析器)
- qrcode 二维码生成器

## 特性

- 自动搜索model目录下的Python文件中的handler
- 可以通过继承约定或者设置`xurl`属性来配置路由
- debug模式下自动侦测文件修改并重新加载
- model目录下的模块使用全局变量task声明定时任务,taskname是任务名称,interval是触发频率，单位是秒

## 配置
- config/users.ini 用户配置，管理员可以添加账户，不支持注册

## 协议

- Apache License (tornado)