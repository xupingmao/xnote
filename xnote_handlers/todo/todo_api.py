# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2026/09/12
# 待办 / 项目 REST API
import xutils

from typing import List
from xnote.core import xauth
from xnote.core.xtemplate import T
from xutils import webutil

from .dao import TodoDao, ProjectDao
from .todo_model import TodoRecord, TodoStatusEnum, TodoPriorityEnum, parse_time_ms
from .project_model import ProjectRecord, ProjectStatusEnum


_STATUS_ACTION_MAP = {
    "start": TodoStatusEnum.in_progress.value,
    "finish": TodoStatusEnum.done.value,
    "cancel": TodoStatusEnum.canceled.value,
    "reset": TodoStatusEnum.not_started.value,
}


class TodoCreateHandler:

    @xauth.login_required()
    def POST(self):
        user_name = xauth.current_name_str()
        user_id = xauth.current_user_id()

        todo = TodoRecord()
        todo.user = user_name
        todo.user_id = user_id
        todo.content = xutils.get_argument_str("content")
        todo.priority = xutils.get_argument_str("priority", "normal")
        todo.project_id = xutils.get_argument_int("project_id", 0)
        todo.begin_time = parse_time_ms(xutils.get_argument_str("begin_time", ""))
        todo.end_time = parse_time_ms(xutils.get_argument_str("end_time", ""))
        todo.tags = xutils.get_argument_str("tags", "[]")

        if todo.content == "":
            return webutil.FailedResult(code="400", message="内容不能为空")

        new_id = TodoDao.create(todo)
        return webutil.SuccessResult(data=new_id)


class TodoUpdateHandler:
    """部分更新待办：只更新传了非空值的字段，其余保持原值

    约定：字符串字段用空串表示“未指定”，project_id 用 -1 表示“未指定”
    （不能用 0，0 是合法的项目ID）
    """

    @xauth.login_required()
    def POST(self):
        user_id = xauth.current_user_id()
        task_id = xutils.get_argument_int("task_id", 0)
        todo = TodoDao.get_by_id(task_id, user_id=user_id)
        if todo is None:
            return webutil.FailedResult(code="404", message="待办不存在")

        content = xutils.get_argument_str("content", "")
        priority = xutils.get_argument_str("priority", "")
        project_id = xutils.get_argument_int("project_id", -1)
        begin_time = xutils.get_argument_str("begin_time", "")
        end_time = xutils.get_argument_str("end_time", "")
        tags = xutils.get_argument_str("tags", "")

        if content != "":
            todo.content = content
        if priority != "":
            todo.priority = priority
        if project_id >= 0:
            todo.project_id = project_id
        if begin_time != "":
            todo.begin_time = parse_time_ms(begin_time)
        if end_time != "":
            todo.end_time = parse_time_ms(end_time)
        if tags != "":
            todo.tags = tags

        TodoDao.update(todo)
        return webutil.SuccessResult(data=task_id)


class TodoDeleteHandler:

    @xauth.login_required()
    def POST(self):
        user_id = xauth.current_user_id()
        task_id = xutils.get_argument_int("task_id", 0)
        TodoDao.delete(task_id, user_id=user_id)
        return webutil.SuccessResult(data=task_id)


class TodoStatusHandler:

    @xauth.login_required()
    def POST(self):
        user_id = xauth.current_user_id()
        task_id = xutils.get_argument_int("task_id", 0)
        action = xutils.get_argument_str("action", "")

        target_status = _STATUS_ACTION_MAP.get(action)
        if target_status is None:
            return webutil.FailedResult(code="400", message="非法的操作")

        TodoDao.update_status(task_id, target_status, user_id=user_id)
        return webutil.SuccessResult(data=dict(task_id=task_id, status=target_status))


class TodoListHandler:

    @xauth.login_required()
    def GET(self):
        user_id = xauth.current_user_id()
        project_id = xutils.get_argument_int("project_id", -1)
        status = xutils.get_argument_str("status", "")
        priority = xutils.get_argument_str("priority", "")
        key = xutils.get_argument_str("key", "")
        begin_start = parse_time_ms(xutils.get_argument_str("begin_start", ""))
        begin_end = parse_time_ms(xutils.get_argument_str("begin_end", ""))
        sort = xutils.get_argument_str("sort", "create_time_desc")
        page = xutils.get_argument_int("page", 1)
        size = xutils.get_argument_int("size", 50)

        items = TodoDao.list_with_filters(
            user_id,
            project_id=None if project_id < 0 else project_id,
            status=status or None,
            priority=priority or None,
            begin_start=begin_start,
            begin_end=begin_end,
            key=key,
            sort=sort,
            offset=(page - 1) * size,
            limit=size)

        total = TodoDao.count_with_filters(
            user_id,
            project_id=None if project_id < 0 else project_id,
            status=status or None,
            priority=priority or None,
            begin_start=begin_start,
            begin_end=begin_end,
            key=key)

        return webutil.SuccessResult(data=dict(items=items, total=total))


class ProjectCreateHandler:

    @xauth.login_required()
    def POST(self):
        user_id = xauth.current_user_id()
        name = xutils.get_argument_str("name")
        if name == "":
            return webutil.FailedResult(code="400", message="项目名称不能为空")

        project = ProjectRecord()
        project.user_id = user_id
        project.name = name
        project.desc = xutils.get_argument_str("desc", "")
        new_id = ProjectDao.create(project)
        return webutil.SuccessResult(data=new_id)


class ProjectUpdateHandler:
    """部分更新项目：只更新传了非空值的字段，其余保持原值"""

    @xauth.login_required()
    def POST(self):
        user_id = xauth.current_user_id()
        project_id = xutils.get_argument_int("project_id", 0)
        project = ProjectDao.get_by_id(project_id, user_id=user_id)
        if project is None:
            return webutil.FailedResult(code="404", message="项目不存在")

        name = xutils.get_argument_str("name", "")
        desc = xutils.get_argument_str("desc", "")
        status = xutils.get_argument_str("status", "")
        if name != "":
            project.name = name
        if desc != "":
            project.desc = desc
        if status != "":
            project.status = status

        ProjectDao.update(project)
        return webutil.SuccessResult(data=project_id)


class ProjectArchiveHandler:

    @xauth.login_required()
    def POST(self):
        user_id = xauth.current_user_id()
        project_id = xutils.get_argument_int("project_id", 0)
        ProjectDao.archive(project_id, user_id=user_id)
        return webutil.SuccessResult(data=project_id)


class ProjectListHandler:

    @xauth.login_required()
    def GET(self):
        user_id = xauth.current_user_id()
        status = xutils.get_argument_str("status", ProjectStatusEnum.active.value)
        projects = ProjectDao.list_by_user(user_id, status=status)
        count_map = TodoDao.count_group_by_project(user_id)
        result = []
        for project in projects:
            item = dict(**project)
            bucket = count_map.get(project.project_id, {})
            item["todo_count"] = sum(bucket.values())
            item["pending_count"] = bucket.get(TodoStatusEnum.not_started.value, 0) + \
                bucket.get(TodoStatusEnum.in_progress.value, 0)
            item["done_count"] = bucket.get(TodoStatusEnum.done.value, 0)
            result.append(item)
        return webutil.SuccessResult(data=result)
