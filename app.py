# encoding=utf-8
import sys
# insert after working dir
sys.path.insert(1, "lib")

import web
import web.xtemplate as xtemplate
import os, socket, sys
from BaseHandler import BaseHandler, reload_template
from FileDB import FileService
import functools
from util import fsutil
from util import dbutil
import xutils
from xutils import *

import json
import time
import config
import webbrowser
import posixpath
import socket
import logging
import traceback
import backup

from autoreload import AutoReloadThread

from web.httpserver import StaticApp
from middlewares import MyStaticMiddleware
from xmanager import ModelManager

class MainHandler(BaseHandler):
    def get(self):
        raise web.seeother("/wiki/")

def get_ip_list(blacklist = []):
    localIp = socket.gethostbyname(socket.gethostname())
    print("localIP:%s" % localIp)
    name, aliaslist, ipList = socket.gethostbyname_ex(socket.gethostname())
    ip_list = []

    for ip in ipList:
        if ip in blacklist:
            continue
        if ip != localIp:
           print("external IP:%s"%ip)
        ip_list.append(ip)

    return ip_list

def main_render_hook(kw):
    """ Main hook for template engine """
    kw["_full_search"] = False
    kw["_search_type"] = "normal"
    # TODO prevent hack
    kw["_is_admin"] = config.IS_ADMIN or web.cookies().get("xuser") == "admin"
    

def notfound():
    raise web.notfound(xtemplate.render("notfound.html"))
    

def check_db():
    xutils.makedirs(config.DB_DIR)
    if not os.path.exists(config.DB_PATH):
        # xutils.touch(config.DB_PATH)
        sql = xutils.readfile(config.SQL_PATH)
        dbutil.execute(config.DB_PATH, sql)

def check_dirs():
    xutils.makedirs(config.LOG_DIR)
    xutils.makedirs("tmp")
    xutils.makedirs("script")
        
def main():
    global app
    global basic_urls

    port = config.PORT
    print("PORT is", os.environ.get("POST"))
    
    if not os.environ.get("PORT"):
        os.environ["PORT"] = port
    
    var_env = dict()

    basic_urls = ["/", "MainHandler"]
    var_env["MainHandler"] = MainHandler

    config.set("host", "localhost")
    config.set("port", port)
    config.set("start_time", time.time())
    # I can reload the system by myself
    app = web.application(list(), var_env, autoreload=False)
    
    # set 404 page
    app.notfound = notfound
    
    # add render hook
    xtemplate.add_render_hook(main_render_hook)
    
    # check database
    check_db()
    check_dirs()

    m = ModelManager(app, var_env, basic_urls)
    m.reload()

    def stop_callback():
        # app.stop()
        m.reload()
        autoreload_thread.clear_watched_files()
        # autoreload_thread.watch_dir("template")
        autoreload_thread.watch_recursive_dir("model")

    # autoreload just reload models
    autoreload_thread = AutoReloadThread(stop_callback)
    autoreload_thread.watch_recursive_dir("model")
    autoreload_thread.start()
    m.run_task()

    # check database backup
    backup.chk_backup()

    app.run(MyStaticMiddleware)

if __name__ == '__main__':
    main()
