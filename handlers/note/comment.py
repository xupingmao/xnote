# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/08/10 23:44:48
# @modified 2021/04/18 15:39:22
import xutils
import xauth
import xtemplate
import xmanager
from xutils import DAO

NOTE_DAO = DAO("note")


def process_comments(comments):
    for comment in comments:
        if comment.content is None:
            continue
        comment.html = xutils.mark_text(comment.content)

class CommentListAjaxHandler:

    def GET(self):
        note_id   = xutils.get_argument("note_id")
        list_type = xutils.get_argument("list_type")
        list_date = xutils.get_argument("list_date")
        user_name = xauth.current_name()

        if list_type == "user":
            comments = NOTE_DAO.list_comments_by_user(user_name, date = list_date)
        else:
            comments  = NOTE_DAO.list_comments(note_id)

        # 处理评论列表
        process_comments(comments)
        return comments

class SaveCommentAjaxHandler:

    @xauth.login_required()
    def POST(self):
        note_id = xutils.get_argument("note_id")
        content = xutils.get_argument("content")
        user    = xauth.current_name()

        NOTE_DAO.save_comment(dict(note_id = note_id, 
            user = user, 
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
            comment_list_date = date,
            comment_list_type = "user")


xurls = (
    r"/note/comments", CommentListAjaxHandler,
    r"/note/comment/save", SaveCommentAjaxHandler,
    r"/note/comment/delete", DeleteCommentAjaxHandler,
    r"/note/mycomments", MyCommentsHandler,
)