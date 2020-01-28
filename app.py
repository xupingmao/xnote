# encoding=utf-8
# @since 2016/12/04
# @modified 2020/01/27 11:04:21
"""xnote - Xnote is Not Only Text Editor
Copyright (C) 2016-2019  xupingmao 578749341@qq.com

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from __future__ import print_function
import os, socket, sys
import json
import time
import webbrowser
import posixpath
import socket
import logging
import traceback
import argparse
# insert after working dir
sys.path.insert(1, "lib")
sys.path.insert(1, "core")
import web
import xutils
import xconfig
import xtables
import xmanager
import xtemplate
import signal
from xutils import *
from autoreload import AutoReloadThread

config = xconfig
DEFAULT_PORT = "1234"

def handle_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="./data")
    parser.add_argument("--delay", default="0")
    parser.add_argument("--ringtone", default="no")
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--webbrowser", default="no")
    parser.add_argument("--debug", default="yes")
    parser.add_argument("--minthreads", default="10")
    parser.add_argument("--useCacheSearch", default="no")
    parser.add_argument("--useUrlencode", default="no")
    parser.add_argument("--devMode", default="no")
    parser.add_argument("--initScript", default="init.py")
    parser.add_argument("--master", default="no")
    parser.add_argument("--test", default="no")

    web.config.debug = False
    args = parser.parse_args(sys.argv[1:])

    # 处理Data目录，创建各种目录
    try:
        xconfig.init(args.data)
    except Exception as e:
        xconfig.errors.append("创建目录失败")
        xutils.print_exc()
    # 端口号
    xconfig.PORT = args.port

    # 延迟加载，避免定时任务重复执行
    delay = int(args.delay)
    time.sleep(delay)

    # 启动提醒
    if args.ringtone == "yes":
        xutils.say("系统启动")
    if args.webbrowser == "yes":
        xconfig.OPEN_IN_BROWSER = True
    if args.debug == "yes":
        xconfig.DEBUG = True
        web.config.debug = True
    if args.useCacheSearch == "yes":
        xconfig.USE_CACHE_SEARCH = True
    if args.useUrlencode == "yes":
        xconfig.USE_URLENCODE = True
    if args.devMode == "yes":
        xconfig.DEV_MODE = True
    if args.test == "yes":
        xconfig.IS_TEST = True

    xconfig.MIN_THREADS = int(args.minthreads)
    xconfig.INIT_SCRIPT = args.initScript
    web.config.minthreads = xconfig.MIN_THREADS

    port = xconfig.PORT
    if port != DEFAULT_PORT:
        # 指定端口优先级最高
        os.environ["PORT"] = port

    if not os.environ.get("PORT"):
        os.environ["PORT"] = port

    xconfig.set("port", port)
    xconfig.set("start_time", xutils.format_datetime())

def handle_signal(signum, frame):
    """处理系统消息
    :arg int signum:
    :arg object frame, current stack frame:
    """
    xutils.log("Signal received: %s" % signum)
    if signum == signal.SIGALRM:
        # 时钟信号
        return
    # 优雅下线
    xmanager.fire("sys.exit")
    exit(0)

def try_init_db():
    try:
        # 初始化数据库
        xtables.init()
        # 初始化leveldb数据库
        dbutil.init()
    except:
        xutils.print_exc()
        xconfig.errors.append("数据库初始化失败")

def try_load_cache():
    try:
        xutils.cacheutil.load_dump()
    except:
        xutils.print_exc()
        xconfig.errors.append("加载缓存失败")

def main():
    global app

    # 处理初始化参数
    handle_args()
    # 初始化日志
    xutils.init_logger()
    # 初始化数据库
    try_init_db()
    # 加载缓存
    try_load_cache()

    # 关闭autoreload使用自己实现的版本
    var_env = dict()
    app = web.application(list(), var_env, autoreload=False)

    # 最后的mapping，用于匹配优先级较低的处理器
    last_mapping = (r"/tools/(.*)", "handlers.tools.tools.handler")
    manager = xmanager.init(app, var_env, last_mapping = last_mapping)
    xmanager.reload()

    # 重新加载template
    xtemplate.reload()

    def reload_callback():
        # 重新加载handlers目录下的所有模块
        xmanager.reload()
        autoreload_thread.clear_watched_files()
        autoreload_thread.watch_dir(xconfig.HANDLERS_DIR, recursive=True)

    # autoreload just reload models
    autoreload_thread = AutoReloadThread(reload_callback)
    autoreload_thread.watch_dir(xconfig.HANDLERS_DIR, recursive=True)
    autoreload_thread.watch_file("core/xtemplate.py")
    autoreload_thread.start()
    # 启动定时任务检查
    manager.run_task()

    # 注册信号响应
    # 键盘终止信号
    signal.signal(signal.SIGINT, handle_signal)
    # kill终止信号
    signal.signal(signal.SIGTERM, handle_signal)
    # 时钟信号
    # signal.signal(signal.SIGALRM, handle_signal)
    # signal.alarm(5)

    # 启动打开浏览器选项
    if xconfig.OPEN_IN_BROWSER:
        webbrowser.open("http://localhost:%s/" % xconfig.PORT)

    app.run()

class LogMiddleware:
    """WSGI middleware for logging the status."""

    PROFILE_SET = set()

    def __init__(self, app):
        self.app = app
        self.format = '%s - - [%s] "%s %s %s" - %s %s ms'
    
        f = BytesIO()
        
        class FakeSocket:
            def makefile(self, *a):
                return f
        
        # take log_date_time_string method from BaseHTTPRequestHandler
        self.log_date_time_string = BaseHTTPRequestHandler(FakeSocket(), None, None).log_date_time_string
        
    def invoke_app(self, environ, start_response):
        start_time = time.time()
        def xstart_response(status, response_headers, *args):
            out = start_response(status, response_headers, *args)
            self.log(status, environ, time.time() - start_time)
            return out
        return self.app(environ, xstart_response)

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '_')
        if path in LogMiddleware.PROFILE_SET:
            vars = dict(f=self.invoke_app, environ=environ, start_response=start_response)
            profile.runctx("r=f(environ, start_response)", globals(), vars, sort="time")
            return vars["r"]
        else:
            return self.invoke_app(environ, start_response)
             
    def log(self, status, environ, cost_time):
        outfile = environ.get('wsgi.errors', web.debug)
        req = environ.get('PATH_INFO', '_') 
        query_string = environ.get("QUERY_STRING", '')
        if query_string != '':
            req += '?' + query_string
        protocol = environ.get('ACTUAL_SERVER_PROTOCOL', '-')
        method = environ.get('REQUEST_METHOD', '-')
        x_forwarded_for = environ.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for is not None:
            host = x_forwarded_for.split(",")[0]
        else:
            host = "%s:%s" % (environ.get('REMOTE_ADDR','-'), 
                              environ.get('REMOTE_PORT','-'))

        time = self.log_date_time_string()

        msg = self.format % (host, time, protocol, method, req, status, int(1000 * cost_time))
        print(utils.safestr(msg), file=outfile)

if __name__ == '__main__':
    main()
