# encoding=utf-8
import os
import xutils

from xnote.core import xtemplate
from xnote.core import xconfig
from xnote.core import xauth

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

    @xauth.login_required("admin")
    def GET(self):
        code = xutils.get_argument_str("code")
        return_json = xutils.get_argument_bool("json")
        output = ""
        if code is None or code == "":
            code = C_TEMPLATE
        else:
            path = os.path.join(xconfig.TMP_DIR, "temp.c")
            xutils.savetofile(path, code)
            status, output = xutils.getstatusoutput("D:\\tcc\\tcc.exe -run %s" % path)

            if return_json:
                return xutils.json_str(status=status, output=output)
        return xtemplate.render("tools/tcc.html", 
            show_aside = False,
            code = code,
            output = output)
            
    def POST(self):
        return self.GET()

xurls = (
    r"/tools/tcc", TccHandler,
)

