# -*- coding:utf-8 -*-  
# Created by xupingmao on 2016/??/??

"""显示代码原文"""
import os
import web
import xauth
import xutils
import xtemplate
import xconfig
from tornado.escape import xhtml_escape
from xutils import u

class ViewSourceHandler:

    def resolve_path(self, path, type=''):
        if type == "script":
            path = os.path.join(xconfig.SCRIPTS_DIR, path)
        path = os.path.abspath(path)
        return xutils.get_real_path(path)

    @xauth.login_required("admin")
    def GET(self):
        template_name = "code/view_source.html"
        path = xutils.get_argument("path", "")
        key  = xutils.get_argument("key", "")
        type = xutils.get_argument("type", "")
        readonly = False
        if path == "":
            return xtemplate.render(template_name, 
                content = "",
                error = "path is empty")
        else:
            error = ""
            warn  = ""
            try:
                path = self.resolve_path(path, type)
                max_file_size = xconfig.MAX_TEXT_SIZE
                if xutils.get_file_size(path, format=False) >= max_file_size:
                    warn = "文件过大，只显示部分内容"
                    readonly = True
                content = xutils.readfile(path, limit = max_file_size)
                # 使用JavaScript来处理搜索关键字高亮问题
                # if key != "":
                #     content = xutils.html_escape(content)
                #     key     = xhtml_escape(key)
                #     content = textutil.replace(content, key, htmlutil.span("?", "search-key"), ignore_case=True, use_template=True)
                return xtemplate.render(template_name, 
                    show_aside = False,
                    readonly = readonly,
                    error = error,
                    warn = warn,
                    pathlist = xutils.splitpath(path),
                    name = os.path.basename(path), 
                    path = path,
                    content = content, lines = content.count("\n")+1)
            except Exception as e:
                xutils.print_exc()
                error = e
            return xtemplate.render(template_name, 
                show_aside = False,
                path = path,
                name = "",
                readonly = readonly,
                error = error, lines = 0, content="")


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
            raise web.seeother("/code/view_source?path=" + xutils.quote_unicode(path))
        

xurls = (
    r"/code/view_source", ViewSourceHandler,
    r"/code/view_source/update", UpdateHandler,
    r"/code/update", UpdateHandler,
    r"/code/edit", ViewSourceHandler
)