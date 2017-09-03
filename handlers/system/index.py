# -*- coding:utf-8 -*-  
# Created by xupingmao on 2016/10
# 

"""Description here"""
from io import StringIO
from handlers.base import *
from xconfig import *
import xconfig
import codecs
import time
import functools
import os
import json
import socket
import os
import autoreload
import xtemplate
import xutils
import xauth

config = xconfig

def get_local_ip(iplist):
    for ip in iplist:
        if ip != "localhost":
            return ip
    return None

def _get_code_lines(dirname):
    if os.path.isfile(dirname):
        text = fsutil.read(dirname)
        return text.count("\n")
    total_lines = 0
    for fname in os.listdir(dirname):
        name, ext = os.path.splitext(fname)
        path = os.path.join(dirname, fname)
        if os.path.isdir(path):
            total_lines += _get_code_lines(path)
            continue
        if ext != ".py":
            continue
        if not os.path.isfile(path):
            continue
        text = fsutil.read(path)
        lines = 0
        for line in text.split("\n"):
            line = line.strip()
            if line != "":
                lines += 1
        total_lines += lines
    return total_lines

def get_code_lines():
    dirname = config.WORKING_DIR
    total_lines = 0
    # total_lines = _get_code_lines(dirname)
    total_lines += _get_code_lines("app.py")
    total_lines += _get_code_lines("autoreload.py")
    total_lines += _get_code_lines("backup.py")
    total_lines += _get_code_lines("ModelManager.py")
    total_lines += _get_code_lines("MyStaticMiddleware.py")
    total_lines += _get_code_lines(os.path.join(dirname, "util"))
    total_lines += _get_code_lines(os.path.join(dirname, "model"))
    return total_lines

def get_ip_list(blacklist = []):
    try:
        # if xutils.is_mac():
            # Mac获取不到
            # return ["127.0.0.1"]
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
    except Exception as e:
        print_exception()
        ip_list = ["localhost"]

    return ip_list

def get_server_ip():
    blacklist = config.get("IP_BLACK_LIST")
    ip_list = get_ip_list(blacklist)
    return ip_list[0]
                
class SysHandler:

    @xauth.login_required()
    def GET(self):
        shell_list = []
        dirname = "scripts"
        if os.path.exists(dirname):
            for fname in os.listdir(dirname):
                fpath = os.path.join(dirname, fname)
                if os.path.isfile(fpath) and fpath.endswith(".bat"):
                    shell_list.append(fpath)
        addr = get_server_ip() + ":" + config.get("PORT")
        return xtemplate.render("system/index.html", 
            addr = addr,
            os = os,
            user = xauth.get_current_user()
        )

    def opendirRequest(self):
        name = self.get_argument("name")
        if os.path.isdir(name):
            fsutil.openDirectory(name)
            ret = { "success": True}
        else:
            ret = {"success": False, "errorMsg": "%s is not a dirname" % name}

        self.write(json.dumps(ret))

    def backup_request(self):
        try:
            backup.zip_xnote()
            return {"success": True}
        except Exception as e:
            print_exception(e)
            return {"success": False, "message": str(e)}

    def export_request(self):
        try:
            backup.zip_new_xnote()
            return  {"success": True}
        except Exception as e:
            return {"success": False}

    def reload_plugins_request(self):
        event.fire("load-plugins")
        event.fire("load-model")
        raise web.seeother("/system/sys")

    def reload_request(self):
        autoreload.force_reload()
        raise web.seeother("/system/sys")

    def default_request(self):
        addr = get_local_ip(config.get("ip_list")) + ":" + config.get("port")
        self.render(backup = backup.get_info(),
            addr = addr
        )
        
handler = SysHandler
searchkey = "sys|系统信息"
name = "系统信息"
description = "展示系统的内存使用、监听地址、数据库大小等内容"

xurls = (
    r"/system/sys",   SysHandler,
    r"/system/index", SysHandler
)