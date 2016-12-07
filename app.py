import web
import web.xtemplate as xtemplate
import os, socket, sys
from BaseHandler import BaseHandler, reload_template
from model.wiki import WikiHandler
from FileDB import FileService
import functools
from util import fsutil
from urllib.parse import unquote
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
from MyStaticMiddleware import MyStaticMiddleware
from ModelManager import ModelManager

        
class MainHandler(BaseHandler):
    def get(self):
        raise web.seeother("/index")

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
    kw["full_search"] = False
    
    
def main():
    global app
    global basic_urls

    port = config.PORT
    
    var_env = dict()

    basic_urls = [
            "/", "MainHandler",
            "/db", "DBHandler",
            "/net", "NetHandler",
            "/wiki/(.*)", "WikiHandler",
        ]
        
    var_env["MainHandler"] = MainHandler
    var_env["WikiHandler"] = WikiHandler


    os.environ["PORT"] = port

    ip_blacklist = config.get("IP_BLACK_LIST")
    ip_list = get_ip_list(blacklist = ip_blacklist) # virtual box host
    config.set("ip_list", ip_list)
    config.set("port", port)
    config.set("start_time", time.time())
    config.set("host", "%s:%s" % (ip_list[0], port))

    # I can reload the system by myself
    app = web.application(list(), var_env, autoreload=False)
    
    xtemplate.add_render_hook(main_render_hook)

    m = ModelManager(app, var_env, basic_urls)
    m.load_model_dir()

    def stop_callback():
        # app.stop()
        m.load_model_dir()
        autoreload_thread.clear_watched_files()
        # autoreload_thread.watch_dir("template")
        autoreload_thread.watch_recursive_dir("model")

    # autoreload just reload models
    autoreload_thread = AutoReloadThread(stop_callback)
    autoreload_thread.watch_recursive_dir("model")
    autoreload_thread.start()

    # check database backup
    backup.chk_backup()

    app.run(MyStaticMiddleware)

if __name__ == '__main__':
    main()
