# encoding=utf-8

import xtemplate
import xutils
import web
import os

from . import sql
from . import pipe
from . import notebook
from . import analyze_html

C_TEMPLATE = """
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int main(int argc, char* argv) {
    return 0;
}
"""

class TccHandler:
    def GET(self):
        args = web.input(code=None, json=None)
        code = args.code
        json = args.json
        output = ""
        if code is None:
            code = C_TEMPLATE
        else:
            xutils.savetofile("tmp\\temp.c", code)
            status, output = xutils.getstatusoutput("D:\\tcc\\tcc.exe -run tmp\\temp.c")

            if json == "true":
                return xutils.json_str(status=status, output=output)
        return xtemplate.render("tools/tcc.html", 
            code = code,
            output = output)
            
    def POST(self):
        return self.GET()
    

class handler:
    
    def GET(self, name):
        name = xutils.unquote(name)
        return xtemplate.render("tools/" + name)

    def POST(self, name):
        return self.GET(name)
        
            
xurls = ("/tools/tcc.html", TccHandler,
         "/tools/sql.html", sql.handler,
         "/tools/pipe.html", pipe.handler,
         "/tools/notebook", notebook.handler,
         "/tools/analyze_html.html", analyze_html.handler,
         "/tools/(.*)", handler)
         
