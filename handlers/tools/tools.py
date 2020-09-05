# encoding=utf-8
import os
import web
import xtemplate
import xutils
import xconfig

C_TEMPLATE = """
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int main(int argc, char* argv) {
    printf("hello,world!");
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
            path = os.path.join(xconfig.TMP_DIR, "temp.c")
            xutils.savetofile(path, code)
            status, output = xutils.getstatusoutput("D:\\tcc\\tcc.exe -run %s" % path)

            if json == "true":
                return xutils.json_str(status=status, output=output)
        return xtemplate.render("tools/tcc.html", 
            show_aside = False,
            code = code,
            output = output)
            
    def POST(self):
        return self.GET()
            
xurls = (r"/tools/tcc", TccHandler)
         
