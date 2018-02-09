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

sys_tools = [
    link("文件管理",   "/fs_data"),
    link("脚本管理",   "/system/script_admin"),
    link("定时任务",   "/system/crontab"),

    link("用户管理", "/system/user/list"),
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
    Storage(name = "系统管理", children = sys_tools, need_login = True, need_admin = True),
    Storage(name = "知识库", children = doc_tools, need_login = True),
    Storage(name = "开发工具", children = dev_tools),
    Storage(name = "图片工具", children = img_tools),
    Storage(name = "编解码工具", children = code_tools),
]

@xutils.cache(key="ip_list", expire=3600)
def get_ip_list(blacklist = []):
    """
    获取本地IP，加上缓存是因为失败的情况下调用非常缓慢
    """
    try:
        hostname = socket.gethostname()
        localIp = socket.gethostbyname(hostname)
        print("localIP:%s" % localIp)
        name, aliaslist, ipList = socket.gethostbyname_ex(hostname)
        ip_list = []
        for ip in ipList:
            if ip in blacklist:
                continue
            if ip != localIp:
               print("external IP:%s"%ip)
            ip_list.append(ip)
    except Exception as e:
        xutils.print_exc()
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


handler = SysHandler
searchkey = "sys|系统信息"
name = "系统信息"
description = "展示系统的内存使用、监听地址、数据库大小等内容"

xurls = (
    r"/system/sys",   SysHandler,
    r"/system/index", SysHandler,
    r"/system/system", SysHandler,
)