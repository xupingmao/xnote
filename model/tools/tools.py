# encoding=utf-8

from web import xtemplate
import xutils
import web
import os

C_TEMPLATE = """
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int main(int argc, char* argv) {
    return 0;
}
"""

class handler:
    __xurl__ = "/tools/(.*)"
    
    def GET(self, name):
        name = xutils.unquote(name)
        if name=="tcc.html":
            return self.tcc()
        elif name=="sql.html":
            from . import sql
            return sql.handler().GET()
        return xtemplate.render("tools/" + name)

    def POST(self, name):
        return self.GET(name)
        
    def tcc(self):
        args = web.input(code=None)
        code = args.code
        output = ""
        if code is None:
            code = C_TEMPLATE
        else:
            xutils.savetofile("tmp\\temp.c", code)
            status, output = xutils.getstatusoutput("D:\\tcc\\tcc.exe -run tmp\\temp.c")
        return xtemplate.render("tools/tcc.html", 
            code = code,
            output = output)