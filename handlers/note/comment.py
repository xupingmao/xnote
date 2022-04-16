# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/08/10 23:44:48
# @modified 2022/04/16 22:36:45
import math
import xconfig
import xutils
import xauth
import xtemplate
import xmanager
from xutils import DAO
from xutils import Storage
from xutils import quote
from xutils import textutil
from xtemplate import T

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
            note = NOTE_DAO.get_by_id(comment.note_id, False)
            if note != None:
                comment.note_name = note.name
                comment.note_url  = note.url

def search_comment_summary(ctx):
    comments = NOTE_DAO.search_comment(user_name = ctx.user_name, keywords = ctx.words)
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
    comments = NOTE_DAO.search_comment(user_name = ctx.user_name, keywords = ctx.words)

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
        note_id   = xutils.get_argument("note_id")
        list_type = xutils.get_argument("list_type")
        resp_type = xutils.get_argument("resp_type")
        list_date = xutils.get_argument("list_date")
        show_note = xutils.get_argument("show_note", type=bool)
        show_edit = xutils.get_argument("show_edit", type=bool)
        page = xutils.get_argument("page", 1, type = int)
        page_max  = 1
        page_size = xconfig.PAGE_SIZE
        user_name = xauth.current_name()
        offset = max(0, page-1) * xconfig.PAGE_SIZE

        if list_type == "user":
            count  = NOTE_DAO.count_comment_by_user(user_name, list_date)
            comments = NOTE_DAO.list_comments_by_user(user_name, 
                date = list_date, offset = offset, 
                limit = page_size)
            page_max = get_page_max(count)
        else:
            comments  = NOTE_DAO.list_comments(note_id, offset = offset, limit = page_size)
            count = NOTE_DAO.count_comment_by_note(note_id)
            page_max = get_page_max(count)

        # 处理评论列表
        process_comments(comments, show_note)

        if resp_type == "html":
            return convert_to_html(comments, show_note, 
                page = page, page_max = page_max, show_edit = show_edit)
        else:
            return comments

class SaveCommentAjaxHandler:

    @xauth.login_required()
    def POST(self):
        note_id = xutils.get_argument("note_id", "")
        content = xutils.get_argument("content", "")
        type    = xutils.get_argument("type")
        user    = xauth.current_name()

        if content == "":
            return dict(code = "400", message = "content参数为空")

        NOTE_DAO.save_comment(Storage(note_id = note_id, 
            user = user, 
            type = type,
            content = content))
        return dict(code = "success", success = True)

class DeleteCommentAjaxHandler:

    def GET(self):
        return self.POST()

    @xauth.login_required()
    def POST(self):
        comment_id = xutils.get_argument("comment_id")
        user       = xauth.current_name()
        comment    = NOTE_DAO.get_comment(comment_id)
        if comment is None:
            return dict(success = False, message = "comment not found")
        if user != comment.user:
            return dict(success = False, message = "unauthorized")
        NOTE_DAO.delete_comment(comment_id)
        return dict(success = True, code = "success")

class MyCommentsHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
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
        comment_id = xutils.get_argument("comment_id", "")

        if p == "edit":
            comment = NOTE_DAO.get_comment(comment_id)
            if comment == None:
                return "评论不存在"
            if comment.user != user_name:
                return "无操作权限"
            return xtemplate.render("note/ajax/comment_edit_dialog.html", comment = comment)
        
        if p == "update":
            comment = NOTE_DAO.get_comment(comment_id)
            if comment == None:
                return dict(code = "404", message = "评论不存在")
            if comment.user != user_name:
                return dict(code = "403", message = "无权限操作")
            content = xutils.get_argument("content", "")
            comment.content = content
            NOTE_DAO.update_comment(comment)
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