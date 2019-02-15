# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/02/15 21:46:37
# @modified 2019/02/15 22:03:36
import xtables
import xtemplate
import xutils

class DictEditHandler:

    def GET(self, name=""):
        table = xtables.get_dict_table()
        item  = table.select_first(where=dict(key=name))
        value = ""
        if item != None:
            value = item.value
        return xtemplate.render("dict/dict_edit.html", 
            name = name, value = value)

    def POST(self, name=""):
        key = xutils.get_argument("name")
        value = xutils.get_argument("value")
        if key != "" and value != "":
            table = xtables.get_dict_table()
            item  = table.select_first(where=dict(key=key))
            if item != None:
                table.update(value = value, where = dict(key = key))
            else:
                table.insert(key = key, value = value)
        return self.GET(name)


xurls = (
    r"/dict/edit/(.+)", DictEditHandler
)