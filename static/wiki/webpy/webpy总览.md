# 总览

## 主要文件

- application.py  （程序框架）
- browser.py      （用于测试webpy的浏览器）
- db.py （数据库接口封装）
- debugerror.py （异常调试页面，可以通过设置debug参数关闭）
- form.py
- http.py
- httpserver.py  (服务器适配层)
- net.py
- py3helpers.py (Python3 兼容层)
- session.py (session支持)
- template.py (webpy模板)
- test.py (用于测试，忽略)
- utils.py (webpy工具类)
- webapi.py (API层，暴露一些接口，包括请求的上下文，参数，cookie，返回值，跳转等)
- webopenid.py (webpy封装的openid库)
- wsgi.py (WSGI接口封装，依赖httpserver)

## 其他

- wsgiserver cherrypy服务器
- contrib 第三方模板接口

## webpy的特点

- 简单而强大
- django让你用django的方法写程序，TurboGears让你用TurboGears 的方式写程序，webpy让你用Python的方式写程序
