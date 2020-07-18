# encoding=utf-8
# Created by xupingmao on 2017/04/16
# @modified 2020/07/18 18:28:29
import math
import xutils
import xtemplate
import xauth
import xtables
import xconfig
from xutils import Storage

class TagHandler:
    
    def GET(self, id):
        creator = xauth.current_name()
        tags    = xutils.call("note.get_tags", creator, id)
        if tags != None:
            tags = [Storage(name=name) for name in tags]
        if not isinstance(tags, list):
            tags = []
        return dict(code="", message="", data=tags)

class TagUpdateHandler:

    @xauth.login_required()
    def POST(self):
        id        = xutils.get_argument("file_id")
        tags_str  = xutils.get_argument("tags")
        user_name = xauth.get_current_name()
        note      = xutils.call("note.get_by_id", id)

        if tags_str is None or tags_str == "":
            xutils.call("note.update_tags", note_id = id, creator = user_name, tags = [])
            return dict(code="success")
        new_tags = tags_str.split(" ")
        xutils.call("note.update_tags", note_id = id, creator = user_name, tags = new_tags)
        return dict(code="success", message="", data="OK")

    def GET(self):
        return self.POST()

class TagNameHandler:

    def GET(self, tagname):
        tagname  = xutils.unquote(tagname)
        page     = xutils.get_argument("page", 1, type=int)
        limit    = xutils.get_argument("limit", xconfig.PAGE_SIZE, type=int)
        offset   = (page-1) * limit

        if xauth.has_login():
            user_name = xauth.get_current_name()
        else:
            user_name = ""
        files = xutils.call("note.list_by_tag", user_name, tagname)
        count = len(files)

        files = files[offset: offset+limit]
        return xtemplate.render("note/page/tagname.html", 
            show_aside = True,
            tagname    = tagname, 
            tags       = tagname,
            files      = files, 
            show_mdate = True,
            page_max   = math.ceil(count / limit), 
            page       = page)


class TagListHandler:

    def GET(self):
        if xauth.has_login():
            user_name = xauth.get_current_name()
            tag_list  = xutils.call("note.list_tag", user_name)
        else:
            tag_list  = xutils.call("note.list_tag", "")
        return xtemplate.render("note/page/taglist.html", 
            html_title = "标签列表",
            show_aside = False,
            tag_list = tag_list)

xurls = (
    r"/note/tag/(\d+)"   , TagHandler,
    r"/note/tag/update"  , TagUpdateHandler,
    r"/note/tagname/(.*)", TagNameHandler,
    r"/note/taglist"     , TagListHandler
)

