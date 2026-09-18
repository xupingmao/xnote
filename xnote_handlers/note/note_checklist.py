# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-06-26 10:49:13
@LastEditors  : xupingmao
@LastEditTime : 2023-09-24 12:16:08
@FilePath     : /xnote/handlers/note/note_checklist.py
@Description  : 清单列表
"""
import xutils

from xutils.base import Storage
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core.xtemplate import T
from .dao import get_by_id as get_note_by_id
from .dao import list_path
from . import dao_tag
from .models import NoteViewContext
from xnote.webui.comment import CommentBox


class ChecklistSearchHandler:

    @xauth.login_required()
    def GET(self):
        note_id = xutils.get_argument_int("note_id")
        note_detail = get_note_by_id(note_id)
        user_name = xauth.current_name()

        if note_detail == None:
            raise Exception("笔记不存在")
        if note_detail.creator != user_name and not note_detail.is_public:
            raise Exception("无访问权限")

        dao_tag.handle_tag_for_note(note_detail)
        kw = NoteViewContext()
        kw.search_type = "checklist"
        kw.search_ext_dict = dict(note_id = note_id)
        kw.comment_list_type = "search"
        kw.pathlist = list_path(note_detail)
        kw.file = note_detail
        kw.show_checklist_search = True
        kw.key = xutils.get_argument_str("key")
        kw.search_key = xutils.get_argument_str("key")
        kw.show_alias = False
        kw.show_relation = False
        kw.show_comment = True
        kw.template_name = "note/page/detail/checklist_detail.html"

        # 评论组件（清单底层复用评论能力），列表按关键词搜索当前笔记的清单项；
        # 列表由前端初始化时通过独立接口异步加载，不再服务端静态输出
        kw.comment_box = CommentBox(
            target_id=note_detail.id,
            list_type="search",
            show_edit=True,
            title=T("清单项"),
            btn_text=T("添加清单项"),
            placeholder=T("请输入清单项..."),
            empty_text=T("暂无清单项~"),
            create_type="list_item",
        )

        return xtemplate.render(**kw)


xurls = (
    r"/note/checklist/search", ChecklistSearchHandler,
)
