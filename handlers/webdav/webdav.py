# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2021/02/14 15:26:54
# @modified 2021/02/14 18:07:03
import web
import xauth
from xutils import logutil

from wsgidav.debug_filter import WsgiDavDebugFilter
from wsgidav.dir_browser import WsgiDavDirBrowser
from wsgidav.error_printer import ErrorPrinter
from wsgidav.http_authenticator import HTTPAuthenticator
from wsgidav.request_resolver import RequestResolver
from wsgidav.wsgidav_app import WsgiDAVApp

ADMIN_PSW = xauth.get_user_password("admin")

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

config = {
    "host": "0.0.0.0",
    "port": 8080,
    "http_authenticator": {
        "accept_basic": True,
    },
    "provider_mapping": {
        "/webdav": "/",
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
        "unquote_path_info": True,  # See issue #8
        # "win_accept_anonymous_options": False,
        # "winxp_accept_root_share_login": False,  # Was True in v2.4
    },

    "dir_browser": {
        "enable": True,
        "icon": True
    },

    "lock_manager": True,
    "simple_dc": {
        "user_mapping": {
            "/webdav": {
                "admin": {
                    "password":ADMIN_PSW,
                    "roles":["admin"]
                }
            }
        }
    },
    "verbose": 1,
}

webdav_app = WsgiDAVApp(config)


"""WSGI(Python Web Server Gateway Interface)接口简单说明

    def application(environ, start_response):
        start_response('200 OK', [('Content-Type', 'text/html')])
        return '<h1>Hello, web!</h1>'
"""

class WebDavHandler:

    def execute(self):
        method = web.ctx.method
        path = web.ctx.environ["PATH_INFO"]

        def start_response(status, response_headers, exc_info=None):
            logutil.trace("webdav", "%s|%s|%s" % (status, method, path))
            web.ctx.status = status
            for header in response_headers:
                web.header(*header)

        for value in webdav_app(web.ctx.environ, start_response):
            yield value

    def __getattr__(self, name):
        return self.execute

xurls = (
    r"/webdav.*", WebDavHandler
)