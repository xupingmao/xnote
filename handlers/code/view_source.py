# -*- coding:utf-8 -*-  
# Created by xupingmao on 2016/??/??
# 

"""显示代码原文"""
from handlers.base import *
from tornado.escape import xhtml_escape

import xutils
import xtemplate

class ViewSourceHandler:

    def GET(self):
        template_name = "code/view_source.html"
        path = xutils.get_argument("path", "")
        key  = xutils.get_argument("key", "")
        if path == "":
            return xtemplate.render(template_name, error = "path is empty")
        else:
            try:
                content = xutils.readfile(path)
                # 使用JavaScript来处理搜索关键字高亮问题
                # if key != "":
                #     content = xutils.html_escape(content)
                #     key     = xhtml_escape(key)
                #     content = textutil.replace(content, key, htmlutil.span("?", "search-key"), ignore_case=True, use_template=True)
                return xtemplate.render(template_name, content = content, lines = content.count("\n")+1)
            except Exception as e:
                xutils.print_stacktrace()
                return xtemplate.render(template_name, error = e, lines = 0, content="")

handler = ViewSourceHandler