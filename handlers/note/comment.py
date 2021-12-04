# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/08/10 23:44:48
# @modified 2021/12/04 22:22:07
import math
import xconfig
import xutils
import xauth
import xtemplate
import xmanager
from xutils import DAO
from xutils import Storage
from xutils import quote
from xtemplate import T

NOTE_DAO = DAO("note")

def get_page_max(count):
    return math.ceil(count/xconfig.PAGE_SIZE)//1

def process_comments(comments, show_note = False):
    for comment in comments:
        if comment.content is None:
            continue
        comment.html = xutils.mark_text(comment.content)

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

def convert_to_html(comments, show_note = False, page = 1, page_max = 1):
    return xtemplate.render("note/ajax/comment_list.html", 
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
        page = xutils.get_argument("page", 1, type = int)
        page_max = 1
        user_name = xauth.current_name()

        if list_type == "user":
            offset = max(0, page-1) * xconfig.PAGE_SIZE
            count  = NOTE_DAO.count_comments_by_user(user_name, list_date)
            comments = NOTE_DAO.list_comments_by_user(user_name, 
                date = list_date, offset = offset, 
                limit = xconfig.PAGE_SIZE)
            page_max = get_page_max(count)
        else:
            comments  = NOTE_DAO.list_comments(note_id)

        # 处理评论列表
        process_comments(comments, show_note)

        if resp_type == "html":
            return convert_to_html(comments, show_note, page = page, page_max = page_max)
        else:
            return comments

class SaveCommentAjaxHandler:

    @xauth.login_required()
    def POST(self):
        note_id = xutils.get_argument("note_id")
        content = xutils.get_argument("content")
        type    = xutils.get_argument("type")
        user    = xauth.current_name()

        NOTE_DAO.save_comment(Storage(note_id = note_id, 
            user = user, 
            type = type,
            content = content))
        return dict(success = True)

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
        return dict(success = True)

class MyCommentsHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        xmanager.add_visit_log(user_name, "/note/mycomments")
        date = xutils.get_argument("date", "")

        return xtemplate.render("note/page/my_comments.html", 
            show_comment_title = False,
            show_comment_create = False,
            show_comment_note = True,
            comment_list_date = date,
            comment_list_type = "user")

xutils.register_func("note.search_comment_detail", search_comment_detail)

xurls = (
    r"/note/comments", CommentListAjaxHandler,
    r"/note/comment/save", SaveCommentAjaxHandler,
    r"/note/comment/delete", DeleteCommentAjaxHandler,
    r"/note/mycomments", MyCommentsHandler,
)