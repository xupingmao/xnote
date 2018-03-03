# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/03/03 12:46:20
# @modified 2018/03/03 15:29:25

from xutils import History

class HistoryHandler(object):
    """docstring for HistoryHandler"""

    def GET(self):
        items = dict()
        for k in History.items:
            v = History.items[k]
            items[k] = list(v)
        return items
        

xurls = (
    r"/system/history", HistoryHandler
)