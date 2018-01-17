# -*- coding:utf-8 -*-  
# Created by xupingmao on 2016/??/??

"""显示代码原文"""
import os
import web
import xauth
import xutils
import xtemplate
from tornado.escape import xhtml_escape

class ViewSourceHandler:

    @xauth.login_required("admin")
    def GET(self):
        template_name = "code/view_source.html"
        path = xutils.get_argument("path", "")
        key  = xutils.get_argument("key", "")
        if path == "":
            return xtemplate.render(template_name, error = "path is empty")
        else:
            error = ""
            try:
                path = xutils.get_real_path(path)
                content = xutils.readfile(path)
                # 使用JavaScript来处理搜索关键字高亮问题
                # if key != "":
                #     content = xutils.html_escape(content)
                #     key     = xhtml_escape(key)
                #     content = textutil.replace(content, key, htmlutil.span("?", "search-key"), ignore_case=True, use_template=True)
                return xtemplate.render(template_name, 
                    pathlist = xutils.splitpath(path),
                    name = os.path.basename(path), 
                    path = path,
                    content = content, lines = content.count("\n")+1)
            except Exception as e:
                xutils.print_stacktrace()
                error = e
            return xtemplate.render(template_name, error = error, lines = 0, content="")


class UpdateHandler(object):
    @xauth.login_required("admin")
    def POST(self):
        path = xutils.get_argument("path", "")
        content = xutils.get_argument("content", "")
        if content == "" or path == "":
            raise web.seeother("/fs/")
        else:
            xutils.savetofile(path, content)
            raise web.seeother("/code/view_source?path=" + xutils.quote_unicode(path))
        

xurls = (
    r"/code/view_source", ViewSourceHandler,
    r"/code/view_source/update", UpdateHandler,
)