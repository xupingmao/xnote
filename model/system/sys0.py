from io import StringIO
from BaseHandler import *
from config import *
import config
import codecs
import time
import functools
import os
from FileDB import FileService
import json
import socket
import backup
import os
import autoreload

def get_memory_usage():
    try:
        if osutil.iswindows():
            pid = os.getpid()
            mem_usage = os.popen("tasklist | findstr %s" % pid).read()
            words = textutil.split_words(mem_usage)
            return words[-2] + " K"
        else:
            pid = os.getpid()
            mem_usage = os.popen("ps -p %s -o rss" % pid).read()
            words = textutil.split_words(mem_usage)
            v = int(words[-1]) * 1024
            return fsutil.format_size(v)
    except Exception as e:
        return None

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
    total_lines += _get_code_lines("FileDB.py")
    total_lines += _get_code_lines("ModelManager.py")
    total_lines += _get_code_lines("MyStaticMiddleware.py")
    total_lines += _get_code_lines(os.path.join(dirname, "util"))
    total_lines += _get_code_lines(os.path.join(dirname, "model"))
    return total_lines


                
class SysHandler(BaseHandler):

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
        # if not hasattr(SysHandler, "_env"):
        #     self.env = env = {}
        #     env['ip_list'] = config.get("ip_list")
        #     env["ip_blacklist"] = config.get("ip_blacklist")
        #     env['port'] = config.get("port")
        #     env["start_time"] = dateutil.getTime(config.get("start_time"))
        #     filepath = FileService.instance().get_path()
        #     filesize = os.stat(filepath).st_size
        #     env["sys_path"] = config.WORKING_DIR
        #     hostname = socket.gethostname()
        #     env["hostname"] = hostname
        #     name, aliaslist, iplist = socket.gethostbyname_ex(hostname)

        #     env["local_ip"] = socket.gethostbyname(hostname)
        #     env["server_ip"] = get_local_ip(config.get("ip_list"))
        #     env["ex_ip"] = iplist
        #     # env["table"] = FileService.getService().getTableDefine("file")
        #     env["code_lines"] = get_code_lines()
        # else:
        #     env = getattr(SysHandler, "_env")
        # env["db_path"] = filepath
        # env["record_size"] = FileService.instance().count()
        # env["db_size"] = fsutil.formatSize(filesize)
        # env["memory_usage"] = get_memory_usage()
        # env['backup'] = backup.get_info()

        # self.render(**env)
        self.render(backup = backup.get_info(),
            server_ip = get_local_ip(config.get("ip_list")),
            port = config.get("port")
        )
        
handler = SysHandler
searchkey = "sys|系统信息"
name = "系统信息"
description = "展示系统的内存使用、监听地址、数据库大小等内容"