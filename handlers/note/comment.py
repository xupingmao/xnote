# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/08/10 23:44:48
# @modified 2021/08/14 00:15:10
import xutils
import xauth
import xtemplate
import xmanager
from xutils import DAO
from xutils import Storage
from xutils import quote
from xtemplate import T

NOTE_DAO = DAO("note")


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
        ctx.tools.append(result)

def search_comment_detail(ctx):
    result = []
    comments = NOTE_DAO.search_comment(user_name = ctx.user_name, keywords = ctx.words)

    process_comments(comments, show_note = True)

    for item in comments:
        item.icon = "fa-comment-o"
        item.name = "#评论 %s" % item.note_name
        item.url  = item.note_url
        result.append(item)

    ctx.notes += result

@xmanager.searchable(r".+")
def on_search_comments(ctx):
    if ctx.category == "default":
        search_comment_summary(ctx)

    if ctx.category == "comment":
        search_comment_detail(ctx)


class CommentListAjaxHandler:

    def GET(self):
        note_id   = xutils.get_argument("note_id")
        list_type = xutils.get_argument("list_type")
        list_date = xutils.get_argument("list_date")
        show_note = xutils.get_argument("show_note", type=bool)
        user_name = xauth.current_name()

        if list_type == "user":
            comments = NOTE_DAO.list_comments_by_user(user_name, date = list_date)
        else:
            comments  = NOTE_DAO.list_comments(note_id)

        # 处理评论列表
        process_comments(comments, show_note)
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