# encoding=utf-8
# Created by xupingmao on 2017/04/21
# @modified 2018/06/30 01:46:36
# 性能测试使用
import xutils
import random

class handler:

    def GET(self):
        # 100M
        total_size = xutils.get_argument("total_size", 100 * 1024 ** 2, type = int)
        size = 0
        buf_size = 1024

        while size < total_size:
            buf = random.choice('0123456789') * buf_size
            size += buf_size
            yield buf
