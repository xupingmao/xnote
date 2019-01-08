# encoding=utf-8
# @since 2016/12/04
# @modified 2019/01/06 22:54:33
"""xnote - Xnote is Not Only Text Editor
Copyright (C) 2016-2017  xupingmao 578749341@qq.com

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
import web
import xutils
import xconfig
import xtables
import xmanager
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

    # 处理Data目录
    xconfig.init(args.data)
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

def main():
    global app
    handle_args()
    port = config.PORT
    if port != DEFAULT_PORT:
        # 指定端口优先级最高
        os.environ["PORT"] = port

    if not os.environ.get("PORT"):
        os.environ["PORT"] = port

    var_env = dict()
    config.set("port", port)
    config.set("start_time", xutils.format_datetime())
    # 关闭autoreload使用自己实现的版本
    app = web.application(list(), var_env, autoreload=False)
    # 初始化数据库
    xtables.init()
    # 加载持久化的缓存
    xutils.cacheutil.load_dump()

    # 最后的mapping，用于匹配优先级较低的处理器
    last_mapping = (r"/tools/(.*)", "handlers.tools.tools.handler")
    manager = xmanager.init(app, var_env, last_mapping = last_mapping)
    xmanager.reload()

    def reload_callback():
        # 重新加载handlers目录下的所有模块
        xmanager.reload()
        autoreload_thread.clear_watched_files()
        autoreload_thread.watch_dir(xconfig.HANDLERS_DIR, recursive=True)

    # autoreload just reload models
    autoreload_thread = AutoReloadThread(reload_callback)
    autoreload_thread.watch_dir(xconfig.HANDLERS_DIR, recursive=True)
    autoreload_thread.watch_file("xtemplate.py")
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

if __name__ == '__main__':
    main()
