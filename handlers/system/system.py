# -*- coding:utf-8 -*-  
# Created by xupingmao on 2016/10
# 

"""Description here"""
from io import StringIO
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

def link(name, url):
    return Storage(name = name, url = url)

debug_tools = [
    link("文件管理",   "/fs_data"),
    link("脚本管理",   "/system/script_admin"),
    link("定时任务",   "/system/crontab"),

    link("用户管理", "/system/user_admin"),
    link("App管理", "/system/app_admin"),

    link("系统信息","/system/monitor"),
    link("template缓存", "/system/template_cache"),
    link("重新加载模块", "/system/reload"),
    link("静音",         "/search/search?key=mute"),
    link("Python Shell", "/system/script/edit?name=test.py"),
    link("Python文档", "/system/modules_info"),
] 

doc_tools = [
    link("标签云", "/file/taglist"),
    link("时光轴", "/tools/timeline"),
    link("记事", "/tools/message?status=created"),
    link("最近更新", "/file/recent_edit"),
    link("我的收藏", "/file/group/marked"),
    link("日历", "/tools/date")
] 

dev_tools = [
    link("代码模板", "/tools/code_template"),
    link("浏览器信息", "/tools/browser_info"),
    link("文本对比", "/tools/js_diff"),
    link("字符串转换", "/tools/string"),
]

img_tools = [
    link("图片合并", "/tools/img_merge"),
    link("图片拆分", "/tools/img_split"),
    link("图像灰度化", "/tools/img2gray"),
]

code_tools = [
    link("base64", "/tools/base64"),
    link("二维码", "/tools/barcode"),
    link("16进制转换", "/tools/hex"),
    link("md5", "/tools/md5"),
]

xconfig.MENU_LIST = [
    Storage(name = "系统管理", children = debug_tools, need_login = True, need_admin = True),
    Storage(name = "知识库", children = doc_tools, need_login = True),
    Storage(name = "开发工具", children = dev_tools),
    Storage(name = "图片工具", children = img_tools),
    Storage(name = "编解码工具", children = code_tools),
]

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

    def GET(self):
        shell_list = []
        dirname = "scripts"
        if os.path.exists(dirname):
            for fname in os.listdir(dirname):
                fpath = os.path.join(dirname, fname)
                if os.path.isfile(fpath) and fpath.endswith(".bat"):
                    shell_list.append(fpath)
        addr = get_server_ip() + ":" + config.get("PORT")
        return xtemplate.render("system/system.html", 
            Storage = Storage,
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


handler = SysHandler
searchkey = "sys|系统信息"
name = "系统信息"
description = "展示系统的内存使用、监听地址、数据库大小等内容"

xurls = (
    r"/system/sys",   SysHandler,
    r"/system/index", SysHandler,
    r"/system/system", SysHandler,
)