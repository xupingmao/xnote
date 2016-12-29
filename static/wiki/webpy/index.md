# 总览

webpy是一个反框架的框架(anti-framework framework)

## 主要文件

- [application.py](_application.md)  （程序框架）
- browser.py      （用于测试webpy的浏览器）
- db.py （数据库接口封装）
- debugerror.py （异常调试页面，可以通过设置debug参数关闭）
- form.py (HTML表单相关)
- http.py 
- httpserver.py  (服务器适配层)
- net.py
- py3helpers.py (Python3 兼容层)
- [session.py](#session.py) (session支持)
- template.py (webpy模板)
- test.py (用于测试，忽略)
- [utils.py](utils.md) (webpy工具类)
- [webapi.py](webapi.md) (API层，暴露一些接口，包括请求的上下文，参数，cookie，返回值，跳转等)
- webopenid.py (webpy封装的openid库)
- [wsgi.py](#wsgi.py) (WSGI接口封装，依赖httpserver)

## 第三方依赖

- wsgiserver cherrypy服务器
- contrib 第三方模板接口

## webpy的特点

- 简单而强大
- django让你用django的方法写程序，TurboGears让你用TurboGears 的方式写程序，webpy让你用Python的方式写程序


## 测试

- webpy使用python的doctest覆盖单元测试

## session.py

- session
- Store session store的基类
- DiskStore,基于磁盘的Store

```

# 构造函数，root：根目录
def __init__(self, root)

# 测试用例
    Store for saving a session on disk.

        >>> import tempfile
        >>> root = tempfile.mkdtemp()
        >>> s = DiskStore(root)
        >>> s['a'] = 'foo'
        >>> s['a']
        'foo'
        >>> time.sleep(0.01)
        >>> s.cleanup(0.01)
        >>> s['a']
        Traceback (most recent call last):
            ...
        KeyError: 'a'
```

- DBStore，基于数据库
- ShelfStore

## wsgi.py

- runfcgi(func, addr)
- runscgi(func, addr)
- runwsgi(func) # 通过命令行参数决定启动上面两个或者httpserver.runsimple