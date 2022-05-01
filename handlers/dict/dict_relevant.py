# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-04-30 11:52:17
@LastEditors  : xupingmao
@LastEditTime : 2022-05-01 12:46:44
@FilePath     : /xnote/handlers/dict/dict_relevant.py
"""

from web.utils import Storage
import xauth
import xutils
import xtemplate

DAO = xutils.DAO("dict_relevant")

class ListHandler:
    
    @xauth.login_required("admin")
    def GET(self):
        key  = xutils.get_argument("key", "")
        page = xutils.get_argument("page", 1, type = int)

        pagesize = 10
        totalsize, words = DAO.list(key = key, page = page, pagesize = pagesize)

        kw = Storage()
        kw.page_size = pagesize
        kw.page_totalsize = totalsize
        kw.words = words
        kw.page = page
        kw.search_type = "relevant_word"

        return xtemplate.render("dict/page/relevant_list.html", **kw)


class EditDialogHandler:

    def GET(self):
        return xtemplate.render("dict/ajax/relevant_edit_dialog.html")

class AddWordsAjaxHandler:

    @xauth.login_required("admin")
    def POST(self):
        words = xutils.get_argument("words", "")
        if words == "":
            return dict(code = "fail", message = "words不能为空")
        
        word_list = words.split()
        if len(word_list) <= 1:
            return dict(code = "fail", message = "至少需要两个单词")

        DAO.add_words(word_list)
        return dict(code = "success")


class DeleteAjaxHandler:

    @xauth.login_required("admin")
    def POST(self):
        word = xutils.get_argument("word", "")
        assert word != ""

        DAO.delete(word)
        return dict(code = "success")


xurls = (
    r"/dict/relevant/list", ListHandler,
    r"/dict/relevant/edit_dialog", EditDialogHandler,
    r"/dict/relevant/add_words", AddWordsAjaxHandler,
    r"/dict/relevant/delete", DeleteAjaxHandler,
)
