# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-04-30 11:52:17
@LastEditors  : xupingmao
@LastEditTime : 2022-04-30 13:08:15
@FilePath     : /xnote/handlers/dict/dict_relevant.py
"""

import xtemplate

class ListHandler:
    
    def GET(self):
        return xtemplate.render("dict/page/relevant_list.html")


class EditDialogHandler:

    def GET(self):
        return xtemplate.render("dict/ajax/relevant_edit_dialog.html")

xurls = (
    r"/dict/relevant/list", ListHandler,
    r"/dict/relevant/edit_dialog", EditDialogHandler,
)
