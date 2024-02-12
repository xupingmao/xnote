# encoding=utf-8
# Created by xupingmao on 2017/04/21
# @modified 2018/11/08 01:33:45
# 性能测试使用,可以生成指定大小的数据块
import xutils
import random
from xnote.core import xauth

class handler:

    @xauth.login_required("admin")
    def GET(self):
        # 100M
        total_size = xutils.get_argument_int("total_size", 100 * 1024 ** 2)
        size = 0
        buf_size = 1024

        while size < total_size:
            buf = random.choice('0123456789') * buf_size
            size += buf_size
            yield buf
