# encoding=utf-8
# Created by xupingmao on 2017/04/16
# @modified 2021/05/22 15:29:04

import xutils
import json

from .dao import get_by_id_creator
from xnote.core import xtemplate
from xnote.core import xauth
from xnote.core import xconfig
from xnote.core import xmanager
from xutils import Storage
from xutils import dbutil, webutil
from xnote.core.xtemplate import T
from . import dao_tag
from .dao_tag import NoteTagInfoDao, NoteTagBindDao
from . import dao as note_dao

class TagUpdateAjaxHandler:

    @xauth.login_required()
    def POST(self):
        note_id = xutils.get_argument_int("file_id")
        tags_str = xutils.get_argument("tags")
        user_name = xauth.get_current_name()
        user_id = xauth.current_user_id()

        if tags_str is None or tags_str == "":
            dao_tag.bind_tags(note_id=note_id, user_id=user_id, tags=[])
            return webutil.SuccessResult()

        assert isinstance(tags_str, str)
        new_tags = tags_str.split()
        dao_tag.bind_tags(note_id=note_id, user_id=user_id, tags=new_tags)
        return webutil.SuccessResult(message="", data="OK")

    def GET(self):
        return self.POST()


class TagInfoHandler:

    @xauth.login_required()
    def GET(self):
        tag_code = xutils.get_argument_str("tag_code")
        page = xutils.get_argument_int("page", 1)
        limit = xutils.get_argument_int("limit", xconfig.PAGE_SIZE)

        offset = (page-1) * limit
        assert offset >= 0
        user_id = xauth.current_user_id()
        files, count = NoteTagBindDao.get_note_page_by_tag(user_id=user_id, tag_code=tag_code, offset=offset, limit=limit)

        kw = Storage()
        kw.tagname = dao_tag.get_name_by_code(tag_code)
        kw.tagcode = tag_code
        kw.tags = tag_code
        kw.files = files
        kw.page = page
        kw.page_size = limit
        kw.page_total = count
        kw.page_url = f"?tag_code={tag_code}&page="

        return xtemplate.render("note/page/taginfo.html", **kw)


class TagListHandler:

    def GET(self):
        if xauth.has_login():
            user_info = xauth.current_user()
            assert user_info != None
            user_name = user_info.name
            user_id = user_info.user_id
            xmanager.add_visit_log(user_name, "/note/taglist")
            tag_category_list = dao_tag.list_tag_category_detail(user_id=user_id)
        else:
            # TODO 公共标签
            tag_category_list = []
        
        kw = Storage()
        kw.html_title = T("标签列表")
        kw.tag_category_list = tag_category_list

        return xtemplate.render("note/page/taglist.html", **kw)


class CreateTagAjaxHandler:

    def create_group_tag(self, user_name, tag_type):
        tag_name = xutils.get_argument_str("tag_name", "")
        group_id = xutils.get_argument_int("group_id")

        if tag_name == "":
            return webutil.FailedResult(code="400", message="tag_name不能为空,请重新输入")
        
        if tag_type == "note" and group_id == None:
            return webutil.FailedResult(code="400", message="group_id不能为空, 请重新输入")

        user_id = xauth.current_user_id()
        tag_bind_list = NoteTagBindDao.get_by_note_id(user_id=user_id, note_id=group_id)

        for tag_bind in tag_bind_list:
            if tag_bind.tag_code == tag_name:
                return webutil.FailedResult(code="500", message="标签已经存在,请重新输入")

        dao_tag.append_tag(note_id=group_id, tag_code=tag_name)
        return webutil.SuccessResult()

    @xauth.login_required()
    def POST(self):
        tag_type = xutils.get_argument("tag_type")
        user_name = xauth.current_name()
        if tag_type in ("group", "note"):
            return self.create_group_tag(user_name, tag_type)

        return webutil.FailedResult(code="fail", message="无效的标签类型")


class DeleteTagAjaxHandler:

    def delete_group_tag(self):
        group_id = xutils.get_argument_int("group_id")
        tag_code_list_str = xutils.get_argument_str("tag_code_list", "[]")
        tag_code_list = json.loads(tag_code_list_str)
        if len(tag_code_list) == 0:
            return webutil.FailedResult(code="400", message="请选择要删除的标签")
        
        user_id = xauth.current_user_id()
        tag_bind_list = NoteTagBindDao.get_by_note_id(user_id=user_id, note_id=group_id)
        new_tags = []
        for bind in tag_bind_list:
            if bind.tag_code not in tag_code_list:
                new_tags.append(bind.tag_code)
        
        NoteTagBindDao.update_tag_and_note(user_id=user_id, note_id=group_id, tags=new_tags)

        return webutil.SuccessResult()

    @xauth.login_required()
    def POST(self):
        tag_type = xutils.get_argument("tag_type")
        if tag_type == "group":
            return self.delete_group_tag()

        return webutil.FailedResult(code="fail", message="无效的标签类型")


class TagListAjaxHandler:

    def list_tag_for_note_v2(self, user_id=0, group_id=0):
        suggest_list = NoteTagInfoDao.list(user_id=user_id, group_id=group_id)
        all_list = NoteTagInfoDao.list(user_id=user_id)
        data = Storage(suggest_list=suggest_list, all_list=all_list)
        return webutil.SuccessResult(data=data)

    @xauth.login_required()
    def GET(self):
        tag_type = xutils.get_argument_str("tag_type", "")
        user_info = xauth.current_user()
        assert user_info != None

        user_id = user_info.user_id

        if tag_type == "group":
            return self.list_tag_for_note_v2(user_id=user_id)
        
        if tag_type == "note":
            group_id = xutils.get_argument_int("group_id")            
            return self.list_tag_for_note_v2(user_id=user_id, group_id=group_id)

        return webutil.FailedResult(code="400", message=f"无效的tag_type({tag_type})")

class BindTagAjaxHandler:

    def bind_group_tag(self):
        group_id = xutils.get_argument_int("group_id")
        tag_names_str = xutils.get_argument_str("tag_names")
        assert isinstance(tag_names_str, str)
        assert group_id != 0
        
        user_name = xauth.current_name()
        book_info = get_by_id_creator(group_id, user_name)
        if book_info == None:
            return webutil.FailedResult(code="500", message="笔记不存在或者无权限")

        user_id = book_info.creator_id
        tag_names = json.loads(tag_names_str)
        NoteTagBindDao.update_tag_and_note(user_id=user_id, note_id=group_id, tags=tag_names)
        return webutil.SuccessResult()
    
    def bind_note_tag(self):
        note_id = xutils.get_argument_int("note_id")
        tag_names_str = xutils.get_argument_str("tag_names")
        
        assert note_id != 0
        assert isinstance(tag_names_str, str)
        
        user_info = xauth.current_user()
        if user_info is None:
            return webutil.FailedResult(code="403", message="用户未登录")
        
        user_name = user_info.name
        book_info = get_by_id_creator(note_id, user_name)
        if book_info == None:
            return webutil.FailedResult(code="500", message="笔记不存在或者无权限")

        user_id = user_info.user_id
        tag_names = json.loads(tag_names_str)
        NoteTagBindDao.update_tag_and_note(user_id=user_id, note_id=note_id, tags=tag_names)
        return webutil.SuccessResult()

    @xauth.login_required()
    def POST(self):
        action = xutils.get_argument_str("action", "")
        tag_type = xutils.get_argument_str("tag_type", "")
        if action == "add_note_to_tag":
            return self.add_note_to_tag()
        if tag_type == "group":
            return self.bind_group_tag()
        if tag_type == "note":
            return self.bind_note_tag()
        return webutil.FailedResult(code="400", message="无效的tag_type")

    def add_note_to_tag(self):
        tag_code = xutils.get_argument_str("tag_code")
        if tag_code == "":
            return webutil.FailedResult(code="400", message="tag_code不存在")
        note_ids_str = xutils.get_argument_str("note_ids")
        note_ids = note_ids_str.split(",")
        if len(note_ids) == 0:
            return webutil.FailedResult(code="400", message="note_ids参数无效")
        for note_id in note_ids:
            dao_tag.append_tag(int(note_id), tag_code)
        return webutil.SuccessResult()


class SuggestTagHandler:

    @xauth.login_required()
    def GET(self):
        group_id = xutils.get_argument_int("group_id")
        user_id = xauth.current_user_id()

        suggest_list = NoteTagInfoDao.list(user_id=user_id, group_id=group_id)
        return webutil.SuccessResult(data=suggest_list)

xurls = (
    # ajax
    r"/note/tag/update", TagUpdateAjaxHandler,
    r"/note/tag/create", CreateTagAjaxHandler,
    r"/note/tag/delete", DeleteTagAjaxHandler,
    r"/note/tag/list", TagListAjaxHandler,
    r"/note/tag/bind", BindTagAjaxHandler,
    r"/note/tag/suggest", SuggestTagHandler,

    # 页面
    r"/note/taginfo", TagInfoHandler,
    r"/note/taglist", TagListHandler,
)
