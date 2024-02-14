# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/08/10 23:44:48
# @modified 2022/04/16 22:36:45
import math
from xnote.core import xconfig
import xutils
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xmanager
from xutils import DAO
from xutils import Storage
from xutils import quote
from xutils import textutil
from xnote.core.xtemplate import T
from . import dao as note_dao
from . import dao_comment
from xutils import webutil

from .dao_comment import search_comment

NOTE_DAO = DAO("note")

def get_page_max(count):
    return int(math.ceil(count/xconfig.PAGE_SIZE))


def search_translator(parser, key0):
    key = key0.lstrip("")
    key = key.rstrip("")
    quoted_key = textutil.quote(key)
    value = textutil.escape_html(key0)
    fmt = "<a class=\"link\" href=\"/search?search_type=comment&key={quoted_key}\">{value}</a>"
    return fmt.format(quoted_key=quoted_key, value=value)

def mark_text(content):
    from xutils.text_parser import TextParser
    from xutils.text_parser import set_img_file_ext
    # 设置图片文集后缀
    set_img_file_ext(xconfig.FS_IMG_EXT_LIST)

    parser = TextParser()
    parser.set_topic_translator(search_translator)
    parser.set_search_translator(search_translator)

    tokens = parser.parse(content)
    return "".join(tokens)

def process_comments(comments, show_note = False):
    for comment in comments:
        if comment.content is None:
            continue
        comment.html = mark_text(comment.content)

        if show_note:
            note = note_dao.get_by_id(comment.note_id, False)
            if note != None:
                comment.note_name = note.name
                comment.note_url  = note.url

def search_comment_summary(ctx):
    comments = dao_comment.search_comment(user_name = ctx.user_name, keywords = ctx.words)
    if len(comments) > 0:
        result = Storage()
        result.name = "搜索到[%s]条评论" % len(comments)
        result.url  = "/search?key=%s&search_type=comment" % quote(ctx.key)
        result.icon = "fa-comments-o"
        result.show_more_link = True
        ctx.messages.append(result)

def search_comment_detail(ctx):
    """搜索评论详细列表接口
    @param {SearchContext} ctx 搜索上下文
    @return None
    """
    result = []
    comments = dao_comment.search_comment(user_name = ctx.user_name, keywords = ctx.words)

    process_comments(comments, show_note = True)

    for item in comments:
        item.icon = "fa-comment-o"
        item.name = "#评论 %s" % item.note_name
        item.url  = item.note_url
        item.mtime = item.ctime
        result.append(item)

    ctx.messages += result

@xmanager.searchable(r".+")
def on_search_comments(ctx):
    if ctx.category == "default":
        search_comment_summary(ctx)

    if ctx.category == "comment":
        search_comment_detail(ctx)

def convert_to_html(comments, show_note = False, page = 1, page_max = 1, show_edit = False):
    return xtemplate.render("note/ajax/comment_list.html", 
        show_comment_edit = show_edit,
        page = page,
        page_max = page_max,
        comments = comments, 
        show_note = show_note)

class CommentListAjaxHandler:

    def GET(self):
        note_id   = xutils.get_argument_str("note_id")
        list_type = xutils.get_argument_str("list_type")
        resp_type = xutils.get_argument_str("resp_type")
        list_date = xutils.get_argument_str("list_date")
        show_note = xutils.get_argument_bool("show_note")
        show_edit = xutils.get_argument_bool("show_edit")
        page = xutils.get_argument_int("page", 1)
        page_max  = 1
        page_size = xconfig.PAGE_SIZE
        user_name = xauth.current_name_str()
        offset = max(0, page-1) * xconfig.PAGE_SIZE

        if list_type == "user":
            count  = dao_comment.count_comments_by_user(user_name, list_date)
            comments = dao_comment.list_comments_by_user(user_name, 
                date = list_date, offset = offset, 
                limit = page_size)
        elif list_type == "search":
            comments = self.search_comments(user_name)
            count = len(comments)
        else:
            assert note_id != None and note_id != ""
            comments  = dao_comment.list_comments(note_id, offset = offset, limit = page_size, user_name=user_name)
            count = dao_comment.count_comment_by_note(note_id)
        
        page_max = get_page_max(count)

        # 处理评论列表
        process_comments(comments, show_note)

        if resp_type == "html":
            return convert_to_html(comments, show_note, 
                page = page, page_max = page_max, show_edit = show_edit)
        else:
            return comments
    
    def search_comments(self, user_name):
        key = xutils.get_argument("key", "")
        note_id = xutils.get_argument("note_id", "")
        keywords = textutil.split_words(key)
        return search_comment(user_name = user_name, keywords = keywords, limit=1000, note_id = note_id)

class SaveCommentAjaxHandler:

    @xauth.login_required()
    def POST(self):
        note_id = xutils.get_argument_int("note_id")
        content = xutils.get_argument_str("content")
        type = xutils.get_argument_str("type")
        user_info = xauth.current_user()

        if user_info == None:
            return webutil.FailedResult(code="403", message="请登录进行操作~")

        if note_id == "":
            return webutil.FailedResult(message="note_id参数为空")
        
        if content == "":
            return dict(code = "400", message = "content参数为空")

        comment = dao_comment.CommentDO()
        comment.user = user_info.name
        comment.user_id = user_info.id
        comment.type = type
        comment.content = content
        comment.note_id = note_id

        dao_comment.create_comment(comment)
        
        return dict(code = "success", success = True)

class DeleteCommentAjaxHandler:

    def GET(self):
        return self.POST()

    @xauth.login_required()
    def POST(self):
        comment_id = xutils.get_argument_str("comment_id")
        user       = xauth.current_name()
        comment    = dao_comment.get_comment(comment_id)
        if comment is None:
            dao_comment.delete_index(comment_id)
            return webutil.SuccessResult()
        if user != comment.user:
            return dict(success = False, message = "unauthorized")
        dao_comment.delete_comment(comment_id)
        return dict(success = True, code = "success")

class MyCommentsHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name_str()
        xmanager.add_visit_log(user_name, "/note/comment/mine")
        date = xutils.get_argument("date", "")

        return xtemplate.render("note/page/comment_user_page.html", 
            show_comment_title = False,
            show_comment_create = False,
            show_comment_note = True,
            comment_list_date = date,
            comment_list_type = "user")

class CommentAjaxHandler:

    @xauth.login_required()
    def GET(self):
        p = xutils.get_argument("p")
        user_name = xauth.current_name()
        comment_id = xutils.get_argument_str("comment_id", "")

        if p == "edit":
            comment = dao_comment.get_comment(comment_id)
            if comment == None:
                return "评论不存在"
            if comment.user != user_name:
                return "无操作权限"
            return xtemplate.render("note/ajax/comment_edit_dialog.html", comment = comment)
        
        if p == "update":
            comment = dao_comment.get_comment(comment_id)
            if comment == None:
                return dict(code = "404", message = "评论不存在")
            if comment.user != user_name:
                return dict(code = "403", message = "无权限操作")
            content = xutils.get_argument_str("content", "")
            comment.content = content
            dao_comment.update_comment(comment)
            return dict(code = "success")
        return "未知的操作"

    def POST(self):
        return self.GET()

xutils.register_func("note.search_comment_detail", search_comment_detail)

xurls = (
    r"/note/comment", CommentAjaxHandler,
    r"/note/comments", CommentListAjaxHandler,
    r"/note/comment/list", CommentListAjaxHandler,
    r"/note/comment/save", SaveCommentAjaxHandler,
    r"/note/comment/delete", DeleteCommentAjaxHandler,
    r"/note/comment/mine", MyCommentsHandler,
)