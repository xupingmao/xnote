# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/04/23
# 

"""Text To Speach"""

import xutils
import xauth

class handler:

    @xauth.login_required("admin")
    def GET(self):
        content = xutils.get_argument("content")
        try:
            xutils.say(content)
            return dict(code="success")
        except Exception as e:
            xutils.print_stacktrace()
            return dict(code="fail", message=str(e))
        finally:
            # 报异常
            # voice.Release()
            # return "OK"
            pass

    def POST(self):
        return self.GET()

