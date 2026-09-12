# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2026/09/12
# 待办评论：复用 note 评论模块（type=todo_task + 独立 target_id 空间做隔离）
import xutils

from xnote.core import xauth, xconfig
from xutils import webutil
from xutils import dateutil

from xnote_handlers.note import dao_comment
from xnote_handlers.note.comment import process_comments, render_to_html, get_page_max

from .dao import TodoDao


COMMENT_TYPE = "todo_task"

# 评论表按 target_id 查询、不按 type 过滤（note 模块的历史设计），
# 而 note_id 与 task_id 是两套独立自增序列，直接复用会串号（甚至跨用户泄露）。
# 这里把待办评论的 target_id 映射到一个不相交的区间，彻底避免与笔记/清单冲突。
COMMENT_TARGET_OFFSET = 10 ** 10


def to_comment_target_id(task_id: int) -> int:
    """task_id -> 评论表的 target_id"""
    return COMMENT_TARGET_OFFSET + task_id


def to_task_id(comment_target_id: int) -> int:
    """评论表的 target_id -> task_id"""
    return comment_target_id - COMMENT_TARGET_OFFSET


class TodoCommentListHandler:
    """待办评论列表（返回 HTML 片段或 JSON）"""

    @xauth.login_required()
    def GET(self):
        user_id = xauth.current_user_id()
        # 沿用评论组件的参数名 note_id（这里是评论表的 target_id）
        target_id = xutils.get_argument_int("note_id", 0)
        task = TodoDao.get_by_id(to_task_id(target_id), user_id=user_id)
        if task is None:
            return webutil.FailedResult(message="待办不存在")

        page = xutils.get_argument_int("page", 1)
        resp_type = xutils.get_argument_str("resp_type")
        comment_order = xutils.get_argument_str("comment_order")
        page_size = xconfig.PAGE_SIZE
        offset = max(0, page - 1) * page_size

        comments, total = dao_comment.list_parent_comments(
            target_id, offset=offset, limit=page_size,
            user_name=xauth.current_name_str(), order=comment_order, type=COMMENT_TYPE)
        process_comments(comments)
        page_max = get_page_max(total)

        if resp_type == "html":
            return render_to_html(comments, page=page, page_max=page_max,
                                  show_edit=True, note_user_id=0)
        return webutil.SuccessResult(data=comments)


class TodoCommentSaveHandler:
    """发表待办评论"""

    @xauth.login_required()
    def POST(self):
        user_info = xauth.current_user()
        user_id = xauth.current_user_id()
        target_id = xutils.get_argument_int("note_id", 0)
        content = xutils.get_argument_str("content")
        files = xutils.get_list_argument("files[]")
        parent_comment_id = xutils.get_argument_int("parent_comment_id", 0)
        ref_comment_id = xutils.get_argument_int("ref_comment_id", 0)
        ref_user_id = xutils.get_argument_int("ref_user_id", 0)

        if user_info is None:
            return webutil.FailedResult(code="403", message="请登录后操作")

        task = TodoDao.get_by_id(to_task_id(target_id), user_id=user_id)
        if task is None:
            return webutil.FailedResult(message="待办不存在")

        if content == "" and len(files) == 0:
            return webutil.FailedResult(code="400", message="评论内容不能为空")

        comment = dao_comment.CommentVO()
        comment.user = user_info.name
        comment.user_id = user_info.id
        comment.type = COMMENT_TYPE
        comment.content = content
        comment.note_id = target_id
        comment.files = files
        comment.parent_comment_id = parent_comment_id
        comment.ref_comment_id = ref_comment_id
        comment.ref_user_id = ref_user_id
        dao_comment.create_comment(comment)

        # 刷新待办的更新时间（替代 note 的 touch_note）
        task.update_time = dateutil.timestamp_ms()
        TodoDao.update(task)

        return webutil.SuccessResult()
