# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2026/09/12
# 待办 / 项目 模块
from . import todo_api
from . import todo_view
from . import todo_comment


xurls = (
    # 页面（/todo 首页=项目列表，/todo?project_id=X=待办列表）
    r"/todo", todo_view.TodoIndexHandler,
    r"/todo/detail", todo_view.TodoDetailHandler,

    # 待办评论（复用 note 评论模块）
    r"/todo/comment/list", todo_comment.TodoCommentListHandler,
    r"/todo/comment/save", todo_comment.TodoCommentSaveHandler,
    r"/todo/comment/delete", todo_comment.TodoCommentDeleteHandler,
    r"/todo/comment/dialog", todo_comment.TodoCommentDialogHandler,

    # 待办 API
    r"/api/todo/create", todo_api.TodoCreateHandler,
    r"/api/todo/update", todo_api.TodoUpdateHandler,
    r"/api/todo/delete", todo_api.TodoDeleteHandler,
    r"/api/todo/status", todo_api.TodoStatusHandler,
    r"/api/todo/list", todo_api.TodoListHandler,

    # 项目 API
    r"/api/project/create", todo_api.ProjectCreateHandler,
    r"/api/project/update", todo_api.ProjectUpdateHandler,
    r"/api/project/archive", todo_api.ProjectArchiveHandler,
    r"/api/project/list", todo_api.ProjectListHandler,
)
