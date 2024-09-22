# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2021/02/14 15:26:54
# @modified 2022/03/04 22:23:22
import web
import xutils
from xnote.core import xmanager
from xnote.core import xconfig
from xnote.core import xauth

import logging
from xutils import logutil

"""wsgidav使用说明
https://wsgidav.readthedocs.io/en/latest/user_guide_lib.html


    from cheroot import wsgi
    from wsgidav.wsgidav_app import WsgiDAVApp

    config = {
        "host": "0.0.0.0",
        "port": 8080,
        "provider_mapping": {
            "/": "/Users/joe/pub",
        },
        "verbose": 1,
    }

    app = WsgiDAVApp(config)

    server_args = {
        "bind_addr": (config["host"], config["port"]),
        "wsgi_app": app,
        }
    server = wsgi.Server(**server_args)
    server.start()

"""

try:
    from wsgidav.wsgidav_app import WsgiDAVApp
except ImportError:
    WsgiDAVApp = None

class MyWebDavApp:
    app   = None
    config = None

    @classmethod
    def reload(cls):
        assert WsgiDAVApp != None
        cls.app = WsgiDAVApp(cls.config)

    @classmethod
    def init(cls, config):
        cls.config = config
        cls.reload()

    @classmethod
    def get_app(cls):
        assert cls.app != None
        return cls.app
    
    @classmethod
    def add_user_mapping(cls, path, user_name, roles):
        config = cls.config
        assert isinstance(config, dict)

        path_info = config["simple_dc"]["user_mapping"].get(path)
        if path_info is None:
            path_info = dict()

        path_info[user_name] = dict(password = xauth.get_user_password(user_name), roles = roles)

        config["simple_dc"]["user_mapping"][path] = path_info

        # print(WEBDAV_CONFIG)

@xutils.log_init_deco("init_webdav_config")
def init_webdav_config():
    if not is_webdav_enabled():
        logging.info("webdav is disabled")
        return
    # from wsgidav.debug_filter import WsgiDavDebugFilter
    from wsgidav.dir_browser import WsgiDavDirBrowser
    from wsgidav.error_printer import ErrorPrinter
    from wsgidav.http_authenticator import HTTPAuthenticator
    from wsgidav.request_resolver import RequestResolver
    from wsgidav.wsgidav_app import WsgiDAVApp

    WEBDAV_CONFIG = {
        "host": "0.0.0.0",
        "port": 8080,
        "http_authenticator": {
            # None: dc.simple_dc.SimpleDomainController(user_mapping)
            # "domain_controller": None,
            # basic认证是不加密的，如果基于HTTPS还可以，HTTP的容易被中间人攻击拦截
            # "accept_basic": True,
            # wsgidav默认使用摘要认证，代码参考 http_authenticator
            "accept_digest": True,  # Allow digest authentication, True or False
            # "default_to_digest": True,  # True (default digest) or False (default basic)
            # Name of a header field that will be accepted as authorized user
            # "trusted_auth_header": None,
        },
        "provider_mapping": {
            "/webdav": "/",
            "/webdav/test": xauth.get_user_data_dir("test", True),
        },
        "middleware_stack": [
            # WsgiDavDebugFilter,
            ErrorPrinter,
            HTTPAuthenticator,
            WsgiDavDirBrowser,  # configured under dir_browser option (see below)
            RequestResolver,  # this must be the last middleware item
        ],

        "hotfixes": {
            # "emulate_win32_lastmod": False,  # True: support Win32LastModifiedTime
            # "re_encode_path_info": None,  # (See issue #73) None: activate on Python 3
            
            # 根据 PEP-333 PATH_INFO应该被服务端unquote，但是有些服务器没有做这个事情
            # 详细参考 https://github.com/mar10/wsgidav/issues/8
            "unquote_path_info": True,  # See issue #8
            # "win_accept_anonymous_options": False,
            # "winxp_accept_root_share_login": False,  # Was True in v2.4
        },

        "dir_browser": {
            "enable": True,
            # "icon": True,
        },

        # "lock_manager": True,
        "lock_storage": True,

        # DC指的是Domain Controller
        # 默认有三个角色：admin/editor/reader
        "simple_dc": {
            "user_mapping": {
                # 参考 add_user_mapping
            }
        },
        "verbose": 1,
    }

    MyWebDavApp.init(WEBDAV_CONFIG)


def is_webdav_enabled():
    return xconfig.get_system_config("webdav") == True

def init_user_mapping():
    MyWebDavApp.add_user_mapping("/webdav",      "admin", ["admin"])
    MyWebDavApp.add_user_mapping("/webdav/test", "test",  ["editor"])

@xmanager.listen("user.update", False)
def reload_on_user_update(ctx = None):
    if not is_webdav_enabled():
        return

    logging.info("reload user_mapping")
    init_user_mapping()

    from wsgidav.wsgidav_app import WsgiDAVApp
    MyWebDavApp.reload()

@xmanager.listen("sys.init")
@xutils.log_init_deco("webdav")
def init_webdav(ctx = None):
    if not is_webdav_enabled():
        logging.info("webdav is disabled")
        return

    # 启动的时候设置一下
    init_user_mapping()

class WebDavHandler:

    def execute(self):
        if not is_webdav_enabled():
            raise web.notfound()

        method = web.ctx.method
        path = web.ctx.environ["PATH_INFO"]

        def start_response(status, response_headers, exc_info=None):
            """WSGI(Python Web Server Gateway Interface)接口简单说明

                def application(environ, start_response):
                    start_response('200 OK', [('Content-Type', 'text/html')])
                    return '<h1>Hello, web!</h1>'
            """
            # print(web.ctx.environ["HTTP_AUTHORIZATION"])
            logutil.trace("webdav", "%s|%s|%s" % (status, method, path))
            web.ctx.status = status
            # print(response_headers)
            for header in response_headers:
                web.header(*header)

        for value in MyWebDavApp.get_app()(web.ctx.environ, start_response):
            # print(value)
            yield value

    def __getattr__(self, name):
        return self.execute

init_webdav_config()

xurls = (
    r"/webdav.*", WebDavHandler
)