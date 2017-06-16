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
import handlers.backup as backup
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

        cmd_list = [];
        # cmd_list.append(Storage(name="切换导航栏样式", url="/system/switch_nav"))
        cmd_list.append(Storage(name="模块信息(pydoc)", url="/system/modules_info"))

        if xauth.is_admin():
            cmd_list.append(Storage(name="系统运行状态", url="/system/monitor"))
            cmd_list.append(Storage(name="文件浏览器", url="/fs/"))
            cmd_list.append(Storage(name="脚本管理", url="/system/script_admin"))
            cmd_list.append(Storage(name="重新加载模块", url="/system/reload"))
            cmd_list.append(Storage(name="Template代码", url="/system/template_cache"))
            cmd_list.append(Storage(name="备份管理", url="/system/backup_info"))
            cmd_list.append(Storage(name="用户管理", url="/system/user_admin"))
            cmd_list.append(Storage(name="定时任务管理", url="/system/crontab"))
            cmd_list.append(Storage(name="首页提醒管理", url="/system/notice_admin"))
            cmd_list.append(Storage(name="App包上传", url="/system/upload_app"))
            cmd_list.append(Storage(name="系统变量管理", url="/system/sys_var_admin"))

        return xtemplate.render("system/sys.html", 
            backup = backup.get_info(),
            # server_ip = get_server_ip(),
            # port = config.get("port"),
            addr = addr,
            cmd_list = cmd_list,
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