# -*- coding:utf-8 -*-  
# Created by xupingmao on 2016/??/??
# @modified 2020/07/11 13:49:58

"""显示代码原文"""
import os
import web
import xauth
import xutils
import xtemplate
import xconfig
from tornado.escape import xhtml_escape
from xutils import u, Storage, fsutil

def can_preview(path):
    name, ext = os.path.splitext(path)
    return ext.lower() in (".md", ".csv")

def handle_embed(kw):
    """处理嵌入式常见"""
    embed  = xutils.get_argument("embed", type=bool)

    kw.show_aside = False
    kw.embed = embed
    if embed:
        kw.show_aside = False
        kw.show_left  = False
        kw.show_menu  = False
        kw.show_search = False
        kw.show_path = False

def handle_args(kw):
    show_path = xutils.get_argument("show_path")
    if show_path:
        kw.show_path = (show_path == "true")

class ViewSourceHandler:

    def resolve_path(self, path, type=''):
        if type == "script":
            path = os.path.join(xconfig.SCRIPTS_DIR, path)
        path = os.path.abspath(path)
        return xutils.get_real_path(path)

    @xauth.login_required("admin")
    def GET(self, path=""):
        template_name = "code/code_edit.html"
        path = xutils.get_argument("path", "")
        key  = xutils.get_argument("key", "")
        type = xutils.get_argument("type", "")
        readonly = False
        
        kw = Storage()
        # 处理嵌入页面
        handle_embed(kw)
        # 处理参数
        handle_args(kw)

        if path == "":
            return xtemplate.render(template_name, 
                content = "",
                error = "path is empty")

        error = ""
        warn  = ""
        try:
            path = self.resolve_path(path, type)
            max_file_size = xconfig.MAX_TEXT_SIZE
            if xutils.get_file_size(path, format=False) >= max_file_size:
                warn = "文件过大，只显示部分内容"
                readonly = True
            content = xutils.readfile(path, limit = max_file_size)
            plugin_name = fsutil.get_relative_path(path, xconfig.PLUGINS_DIR)
            # 使用JavaScript来处理搜索关键字高亮问题
            # if key != "":
            #     content = xutils.html_escape(content)
            #     key     = xhtml_escape(key)
            #     content = textutil.replace(content, key, htmlutil.span("?", "search-key"), ignore_case=True, use_template=True)
            return xtemplate.render(template_name, 
                show_preview = can_preview(path),
                readonly = readonly,
                error = error,
                warn = warn,
                pathlist = xutils.splitpath(path),
                name = os.path.basename(path), 
                path = path,
                content = content, 
                plugin_name = plugin_name,
                lines = content.count("\n")+1, **kw)
        except Exception as e:
            xutils.print_exc()
            error = e
        return xtemplate.render(template_name, 
            path = path,
            name = "",
            readonly = readonly,
            error = error, lines = 0, content="", **kw)


class UpdateHandler(object):
    
    @xauth.login_required("admin")
    def POST(self):
        path = xutils.get_argument("path", "")
        content = xutils.get_argument("content", "")
        if content == "" or path == "":
            raise web.seeother("/fs/")
        else:
            content = content.replace("\r\n", "\n")
            xutils.savetofile(path, content)
            raise web.seeother("/code/edit?path=" + xutils.quote(path))
        

xurls = (
    r"/code/view_source", ViewSourceHandler,
    r"/code/view_source/update", UpdateHandler,
    r"/code/update", UpdateHandler,
    r"/code/edit", ViewSourceHandler
)