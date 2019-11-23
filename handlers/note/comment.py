# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/08/10 23:44:48
# @modified 2019/11/23 16:20:43
import xutils
import xauth
from xutils import DAO

NOTE_DAO = DAO("note")

class CommentListHandler:

    def GET(self):
        note_id = xutils.get_argument("note_id")
        comments = NOTE_DAO.list_comments(note_id)
        for comment in comments:
            if comment.content is None:
                continue
            comment.html = xutils.mark_text(comment.content)
        return comments

class SaveCommentHandler:

    @xauth.login_required()
    def POST(self):
        note_id = xutils.get_argument("note_id")
        content = xutils.get_argument("content")
        user    = xauth.current_name()

        NOTE_DAO.save_comment(dict(note_id = note_id, 
            ctime = xutils.format_time(),
            user = user, 
            content = content))
        return dict(success = True)

class DeleteCommentHandler:

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

xurls = (
    r"/note/comments", CommentListHandler,
    r"/note/comment/save", SaveCommentHandler,
    r"/note/comment/delete", DeleteCommentHandler
)