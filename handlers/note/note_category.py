# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-07-15 22:58:53
@LastEditors  : xupingmao
@LastEditTime : 2022-07-15 23:00:50
@FilePath     : /xnote/handlers/note/note_category.py
@Description  : 笔记本类型
"""
import xauth
import xtemplate
import xutils

NOTE_DAO = xutils.DAO("note")


class NoteCategory:

    def __init__(self, code, name):
        self.name = "%s-%s" % (code, name)
        self.url  = "/note/group?category=" + code
        self.icon = ""
        self.priority = 0
        self.is_deleted = 0
        self.size = 0
        self.show_next = True
        self.icon = "fa-folder"
        self.badge_info = ""

def get_ddc_category_list():
    # TODO 配置化
    # 主要参考的是：杜威十进制分类法和国际十进制分类法
    category_list = []
    category_list.append(NoteCategory("000", "计算机科学、资讯和总类"))
    category_list.append(NoteCategory("100", "哲学和心理学"))
    category_list.append(NoteCategory("200", "宗教"))
    category_list.append(NoteCategory("300", "社会科学"))
    category_list.append(NoteCategory("400", "语言"))
    category_list.append(NoteCategory("500", "数学和自然科学"))
    category_list.append(NoteCategory("600", "应用科学、医学、技术"))
    category_list.append(NoteCategory("700", "艺术与休闲"))
    category_list.append(NoteCategory("800", "文学"))
    category_list.append(NoteCategory("900", "历史、地理和传记"))
    return category_list


class CategoryHandler:

    @xauth.login_required()
    def GET(self):
        files = get_ddc_category_list()
        cat_type = xutils.get_argument("type", "ddc")

        root = NOTE_DAO.get_root()
        return xtemplate.render("note/page/category.html", 
            file = root, 
            title = u"杜威十进制分类法(DDC)",
            pathlist = [root],
            show_path_list = True,
            show_size = True,
            parent_id = 0,
            files = files)


xurls = (
    r"/note/category", CategoryHandler,
)
