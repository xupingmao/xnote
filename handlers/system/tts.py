# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/04/23
# 

"""Text To Speach"""

import xutils
from handlers.base import BaseHandler

class handler(BaseHandler):

    def default_request(self):
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