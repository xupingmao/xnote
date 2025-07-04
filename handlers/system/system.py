# -*- coding:utf-8 -*-
# Created by xupingmao on 2016/10
# @modified 2022/02/26 11:27:37
"""System functions"""
import os
import web
import xutils
import subprocess
import logging

from . import system_config
from xnote.core import xconfig
from xnote.core import xtemplate
from xnote.core import xauth
from xnote.core import xmanager
from xutils import Storage
from xutils import webutil
from .system_config import AppLink

system_config.init()

class IndexHandler:

    def GET(self):
        arg_show_back = xutils.get_argument_bool("show_back")
        arg_show_menu = xutils.get_argument_bool("show_menu", default_value=True)
        user_name = xauth.current_name()
        menu_list = []

        def filter_link_func(link: AppLink):
            if link.is_guest:
                return user_name is None
            if link.is_user:
                return user_name != None
            if link.user == "" or link.user == None:
                return True
            return link.user == user_name

        for category in xconfig.MENU_LIST:
            children = category.children
            if len(children) == 0:
                continue
            children = list(filter(filter_link_func, children))
            menu_list.append(Storage(name=category.name, children=children))

        kw = Storage()
        kw.Storage = Storage
        kw.user = xauth.get_current_user()
        kw.menu_list = menu_list
        kw.html_title = "系统"
        kw.show_back = arg_show_back
        kw.show_menu = arg_show_menu

        return xtemplate.render("system/page/system_index.html", **kw)


class AdminHandler:

    @xauth.login_required("admin")
    def GET(self):
        if webutil.is_desktop_client():
            raise web.found("/system/info")
        return xtemplate.render("system/page/system_admin.html")


class ReloadHandler:

    @xauth.admin_required()
    def GET(self):
        # autoreload will load new handlers
        import web

        runtime_id = xutils.get_argument_str("runtime_id")
        if runtime_id == xconfig.RUNTIME_ID:
            # autoreload.reload()
            xmanager.restart()
            raise web.seeother("/system/index")
        else:
            result = webutil.SuccessResult()
            result.status = "running"
            return result

    def POST(self):
        return self.GET()


class PullCodeHandler:

    @xauth.login_required("admin")
    def GET(self):
        check_git = os.system("git --version")
        if check_git != 0:
            return webutil.FailedResult(code="400", message="系统没有安装git,无法升级")
        
        process = subprocess.Popen("git pull", shell=True, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
        # subprocess.Popen默认异步执行
        # 等待5秒等进程执行完成
        process.wait(timeout=5)
        if process.returncode not in (0, None):
            err_msg = f"returncode:({process.returncode})"
            if process.stderr != None:
                err_msg = process.stderr.read()
            elif process.stdout != None:
                err_msg = process.stdout.read()
            return webutil.FailedResult(code="500", message=f"升级失败:{err_msg}")
        
        logging.info("pull code success")
        return webutil.SuccessResult()
    
    def POST(self):
        return self.GET()

class UserCssHandler:

    def GET(self):
        web.header("Content-Type", "text/css")
        environ = web.ctx.environ
        path = os.path.join(xconfig.SCRIPTS_DIR, "user.css")
        web.header("Cache-Control", "max-age=3600")

        if not os.path.exists(path):
            return b''

        etag = '"%s"' % os.path.getmtime(path)
        client_etag = environ.get('HTTP_IF_NONE_MATCH')
        web.header("Etag", etag)
        if etag == client_etag:
            web.ctx.status = "304 Not Modified"
            return b''  # 其实webpy已经通过yield空bytes来避免None
        return xutils.readfile(path)
        # return xconfig.get("USER_CSS", "")


class UserJsHandler:

    def GET(self):
        web.header("Content-Type", "application/javascript")
        web.header("Cache-Control", "max-age=3600")
        path = os.path.join(xconfig.SCRIPTS_DIR, "user.js")
        if not os.path.exists(path):
            return ""
        return xutils.readfile(path)


xutils.register_func("url:/system/index", IndexHandler)

xurls = (
    r"/system/sys",   IndexHandler,
    r"/system/index", IndexHandler,
    r"/system/admin", AdminHandler,
    r"/system/system", IndexHandler,
    r"/system/reload", ReloadHandler,
    r"/system/pull_code", PullCodeHandler,
    r"/system/user\.css", UserCssHandler,
    r"/system/user\.js", UserJsHandler,
)
