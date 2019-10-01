# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/08/10 23:44:48
# @modified 2019/10/01 16:01:19
import xutils
import xauth
from xutils import DAO

NOTE_DAO = DAO("note")

class CommentListHandler:

    def GET(self):
        note_id = xutils.get_argument("note_id")
        comments = NOTE_DAO.list_comments(note_id)
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

xurls = (
    r"/note/comments", CommentListHandler,
    r"/note/comment/save", SaveCommentHandler
)