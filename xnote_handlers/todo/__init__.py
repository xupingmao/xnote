# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2026/09/12
# 待办 / 项目 模块
from . import todo_api
from . import todo_view


xurls = (
    # 页面（/todo 首页=项目列表，/todo/task?project_id=X=该项目待办列表）
    r"/todo", todo_view.TodoProjectHandler,
    r"/todo/task", todo_view.TodoTaskHandler,
    r"/todo/detail", todo_view.TodoDetailHandler,

    # 待办评论（与笔记共用 xnote_handlers/comment 模块，type=todo_task 区分）
    # 路由在 xnote_handlers/comment/__init__.py 统一注册(/comment/*)

    # 待办 API
    r"/api/v1/todo/create", todo_api.TodoCreateHandler,
    r"/api/v1/todo/update", todo_api.TodoUpdateHandler,
    r"/api/v1/todo/delete", todo_api.TodoDeleteHandler,
    r"/api/v1/todo/status", todo_api.TodoStatusHandler,
    r"/api/v1/todo/list", todo_api.TodoListHandler,

    # 项目 API
    r"/api/v1/project/create", todo_api.ProjectCreateHandler,
    r"/api/v1/project/update", todo_api.ProjectUpdateHandler,
    r"/api/v1/project/archive", todo_api.ProjectArchiveHandler,
    r"/api/v1/project/list", todo_api.ProjectListHandler,
)
