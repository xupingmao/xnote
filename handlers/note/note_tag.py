# encoding=utf-8
# Created by xupingmao on 2017/04/16
# @modified 2021/05/22 15:29:04

import math
from .dao import get_by_id_creator
import xutils
import xtemplate
import xauth
import xconfig
import xmanager
import json
from xutils import Storage
from xutils import dbutil
from xtemplate import T
from . import dao_tag

tag_db = dbutil.get_table("note_tag_meta")

class TagAjaxHandler:

    @xauth.login_required()
    def GET(self, id):
        creator = xauth.current_name()
        tags = dao_tag.get_tags(creator, id)
        if tags != None:
            tags = [Storage(code=code, name=dao_tag.get_name_by_code(code)) for code in tags]
        if not isinstance(tags, list):
            tags = []
        return dict(code="", message="", data=tags)


class TagUpdateAjaxHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("file_id")
        tags_str = xutils.get_argument("tags")
        user_name = xauth.get_current_name()
        note = xutils.call("note.get_by_id", id)

        if tags_str is None or tags_str == "":
            xutils.call("note.update_tags", note_id=id,
                        creator=user_name, tags=[])
            return dict(code="success")
        new_tags = tags_str.split(" ")
        xutils.call("note.update_tags", note_id=id,
                    creator=user_name, tags=new_tags)
        return dict(code="success", message="", data="OK")

    def GET(self):
        return self.POST()


class TagNameHandler:

    def GET(self, tagname):
        tagname = xutils.unquote(tagname)
        page = xutils.get_argument("page", 1, type=int)
        limit = xutils.get_argument("limit", xconfig.PAGE_SIZE, type=int)

        assert isinstance(page, int)
        assert isinstance(limit, int)

        offset = (page-1) * limit

        if xauth.has_login():
            user_name = xauth.get_current_name()
        else:
            user_name = ""
        files = xutils.call("note.list_by_tag", user_name, tagname)
        count = len(files)

        files = files[offset: offset+limit]

        kw = Storage()
        kw.tagname = dao_tag.get_name_by_code(tagname)
        kw.tags = tagname
        kw.files = files
        kw.page = page
        kw.page_max = math.ceil(count/limit)
        kw.show_mdate = True

        return xtemplate.render("note/page/tagname.html", **kw)


class TagListHandler:

    def GET(self):
        if xauth.has_login():
            user_name = xauth.get_current_name()
            assert isinstance(user_name, str)

            tag_list = dao_tag.list_tag(user_name)
            xmanager.add_visit_log(user_name, "/note/taglist")
        else:
            tag_list = dao_tag.list_tag("")
        
        kw = Storage()
        kw.html_title = T("标签列表")
        kw.tag_list = tag_list
        kw.system_tag_list = dao_tag.get_system_tag_list(tag_list)

        return xtemplate.render("note/page/taglist.html", **kw)


class CreateTagAjaxHandler:

    def create_group_tag(self, user_name, tag_type):
        tag_name = xutils.get_argument("tag_name", "")
        group_id = xutils.get_argument("group_id", "")

        if group_id == "":
            group_id = None

        if tag_name == "":
            return dict(code="400", message="tag_name不能为空,请重新输入")
        
        if tag_type == "note" and group_id == None:
            return dict(code="400", message="group_id不能为空, 请重新输入")

        obj = dict(
            tag_type=tag_type,
            tag_name=tag_name,
            user=user_name,
            group_id=group_id,
            book_id=group_id,
        )

        tag_meta = dao_tag.get_tag_meta_by_name(user_name, tag_name, tag_type=tag_type, group_id=group_id)
        if tag_meta != None:
            return dict(code="500", message="标签已经存在,请重新输入")

        tag_db.insert(obj, id_type="auto_increment")
        return dict(code="success")

    @xauth.login_required()
    def POST(self):
        tag_type = xutils.get_argument("tag_type")
        user_name = xauth.current_name()
        if tag_type in ("group", "note"):
            return self.create_group_tag(user_name, tag_type)

        return dict(code="fail", message="无效的标签类型")


class DeleteTagAjaxHandler:

    def delete_group_tag(self, user_name):
        tag_ids_str = xutils.get_argument("tag_ids", "[]")
        tag_ids = json.loads(tag_ids_str)
        if len(tag_ids) == 0:
            return dict(code="400", message="请选择要删除的标签")
        
        user_name = xauth.current_name()
        for id in tag_ids:
            tag_db.delete_by_id(id, user_name=user_name)

        return dict(code="success")

    @xauth.login_required()
    def POST(self):
        tag_type = xutils.get_argument("tag_type")
        user_name = xauth.current_name()
        if tag_type == "group":
            return self.delete_group_tag(user_name)

        return dict(code="fail", message="无效的标签类型")


class TagListAjaxHandler:

    @xauth.login_required()
    def GET(self):
        tag_type = xutils.get_argument("tag_type", "")
        user_name = xauth.current_name()
        if tag_type == "group":
            data_list = dao_tag.list_tag_meta(limit=1000, user_name=user_name)
            return dict(code="success", data = data_list)
        
        if tag_type == "note":
            group_id = xutils.get_argument("group_id", "")
            data_list = dao_tag.list_tag_meta(limit=1000, user_name=user_name, tag_type="note", group_id=group_id)
            return dict(code="success", data = data_list)

        return dict(code="400", message="无效的tag_type(%s)" % tag_type)

class BindTagAjaxHandler:

    def bind_group_tag(self):
        group_id = xutils.get_argument("group_id", "")
        tag_names_str = xutils.get_argument("tag_names", "")

        assert group_id != ""
        
        user_name = xauth.current_name()
        book_info = get_by_id_creator(group_id, user_name)
        if book_info == None:
            return dict(code="500", message="笔记不存在或者无权限")

        tag_names = json.loads(tag_names_str)
        dao_tag.bind_tags(user_name, group_id, tag_names, tag_type="group")
        return dict(code="success")
    
    def bind_note_tag(self):
        note_id = xutils.get_argument("note_id", "")
        tag_names_str = xutils.get_argument("tag_names", "")

        assert note_id != ""
        
        user_name = xauth.current_name()
        book_info = get_by_id_creator(note_id, user_name)
        if book_info == None:
            return dict(code="500", message="笔记不存在或者无权限")

        tag_names = json.loads(tag_names_str)
        dao_tag.bind_tags(user_name, note_id, tag_names, tag_type="note")
        return dict(code="success")

    @xauth.login_required()
    def POST(self):
        tag_type = xutils.get_argument("tag_type", "")
        if tag_type == "group":
            return self.bind_group_tag()
        if tag_type == "note":
            return self.bind_note_tag()
        return dict(code="400", message="无效的tag_type")

xurls = (
    # ajax
    r"/note/tag/(\d+)", TagAjaxHandler,
    r"/note/tag/update", TagUpdateAjaxHandler,
    r"/note/tag/create", CreateTagAjaxHandler,
    r"/note/tag/delete", DeleteTagAjaxHandler,
    r"/note/tag/list", TagListAjaxHandler,
    r"/note/tag/bind", BindTagAjaxHandler,

    # 页面
    r"/note/tagname/(.*)", TagNameHandler,
    r"/note/taglist", TagListHandler
)
