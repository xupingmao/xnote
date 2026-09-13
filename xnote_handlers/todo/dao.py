# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2026/09/12
# 待办 / 项目 数据访问层
from typing import Any, Dict, List, Optional

from xnote.core import xtables
from xutils import dateutil

from .todo_model import TodoRecord, TodoStatusEnum, TodoPriorityEnum
from .project_model import ProjectRecord, ProjectStatusEnum


_todo_db = xtables.get_table_by_name("todo_task")
_project_db = xtables.get_table_by_name("todo_project")


class TodoDao:
    """待办数据访问"""

    @classmethod
    def create(cls, todo: TodoRecord) -> int:
        now = dateutil.timestamp_ms()
        todo.create_time = now
        todo.update_time = now
        return _todo_db.insert_record(todo)

    @classmethod
    def create_with_id(cls, todo: TodoRecord, task_id: int) -> int:
        """指定主键 task_id 插入。

        迁移场景用它把消息ID直接作为 task_id，配合调用方的存在性检查即可保证重试幂等。
        时间字段保留调用方设置的原始值，未设置(0)时才补当前时间。
        """
        now = dateutil.timestamp_ms()
        if todo.create_time == 0:
            todo.create_time = now
        if todo.update_time == 0:
            todo.update_time = now
        save_dict = todo.to_save_dict()
        save_dict["task_id"] = task_id
        return _todo_db.insert(**save_dict)

    @classmethod
    def get_by_id(cls, task_id: int, user_id: int = 0) -> Optional[TodoRecord]:
        row = _todo_db.select_first(where=dict(task_id=task_id))
        todo = TodoRecord.from_dict_or_None(row)
        if todo is None:
            return None
        if user_id != 0 and todo.user_id != user_id:
            return None
        return todo

    @classmethod
    def update(cls, todo: TodoRecord) -> int:
        todo.update_time = dateutil.timestamp_ms()
        save = todo.to_save_dict()
        save.pop("task_id", None)
        return _todo_db.update(where=dict(task_id=todo.task_id), **save)

    @classmethod
    def delete(cls, task_id: int, user_id: int = 0) -> int:
        """软删除"""
        return _todo_db.update(where=dict(task_id=task_id, user_id=user_id),
                               is_deleted=1,
                               update_time=dateutil.timestamp_ms())

    @classmethod
    def _status_fields(cls, status: str, now: int) -> Dict[str, Any]:
        """状态变更时需要同步维护的字段（状态 + 完成时间）"""
        fields = dict(status=status)  # type: Dict[str, Any]
        if status == TodoStatusEnum.done.value:
            fields["done_time"] = now
        elif status == TodoStatusEnum.not_started.value:
            fields["done_time"] = 0
        return fields

    @classmethod
    def update_status(cls, task_id: int, status: str, user_id: int = 0) -> int:
        now = dateutil.timestamp_ms()
        fields = cls._status_fields(status, now)
        fields["update_time"] = now
        return _todo_db.update(where=dict(task_id=task_id, user_id=user_id), **fields)

    @classmethod
    def apply_status(cls, task: TodoRecord, status: str) -> None:
        """设置记录的状态，并同步维护完成时间（update_time 由 update 维护）"""
        fields = cls._status_fields(status, dateutil.timestamp_ms())
        task.status = status
        task.done_time = fields.get("done_time", task.done_time)

    @classmethod
    def update_comment_count(cls, task_id: int, comment_count: int) -> int:
        """更新待办的评论数量（调用方需自行校验权限）"""
        return _todo_db.update(where=dict(task_id=task_id), comment_count=comment_count)

    # ---------- 查询 ----------

    @classmethod
    def _build_where(cls, user_id: int, project_id: Optional[int] = None,
                     status: Optional[str] = None,
                     status_list: Optional[List[str]] = None,
                     priority: Optional[str] = None,
                     begin_start: int = 0, begin_end: int = 0,
                     is_deleted: int = 0) -> "tuple":
        where = "user_id=$user_id AND is_deleted=$is_deleted"
        vars = dict(user_id=user_id, is_deleted=is_deleted)  # type: Dict[str, Any]
        if project_id is not None:
            where += " AND project_id=$project_id"
            vars["project_id"] = project_id
        if status is not None and status != "":
            where += " AND status=$status"
            vars["status"] = status
        if status_list:
            # web.py 会把 list 展开成 (a, b)
            where += " AND status IN $status_list"
            vars["status_list"] = status_list
        if priority is not None and priority != "":
            where += " AND priority=$priority"
            vars["priority"] = priority
        if begin_start:
            where += " AND begin_time>=$begin_start"
            vars["begin_start"] = begin_start
        if begin_end:
            where += " AND begin_time<$begin_end"
            vars["begin_end"] = begin_end
        return where, vars

    @classmethod
    def list_by_project(cls, user_id: int, project_id: int,
                        status: Optional[str] = None,
                        offset: int = 0, limit: int = 50,
                        order: str = "begin_time asc") -> List[TodoRecord]:
        where, vars = cls._build_where(user_id, project_id=project_id, status=status)
        rows = _todo_db.select(where=where, vars=vars, offset=offset,
                               limit=limit, order=order)
        return TodoRecord.from_dict_list(rows)

    @classmethod
    def list_by_status(cls, user_id: int, status: str,
                       offset: int = 0, limit: int = 50,
                       order: str = "create_time desc") -> List[TodoRecord]:
        where, vars = cls._build_where(user_id, status=status)
        rows = _todo_db.select(where=where, vars=vars, offset=offset,
                               limit=limit, order=order)
        return TodoRecord.from_dict_list(rows)

    @classmethod
    def list_by_priority(cls, user_id: int, priority: str,
                         offset: int = 0, limit: int = 50,
                         order: str = "priority asc") -> List[TodoRecord]:
        where, vars = cls._build_where(user_id, priority=priority)
        rows = _todo_db.select(where=where, vars=vars, offset=offset,
                               limit=limit, order=order)
        return TodoRecord.from_dict_list(rows)

    @classmethod
    def list_by_time_range(cls, user_id: int, begin_start: int, begin_end: int,
                           offset: int = 0, limit: int = 50,
                           order: str = "begin_time asc") -> List[TodoRecord]:
        where, vars = cls._build_where(user_id, begin_start=begin_start,
                                       begin_end=begin_end)
        rows = _todo_db.select(where=where, vars=vars, offset=offset,
                               limit=limit, order=order)
        return TodoRecord.from_dict_list(rows)

    @classmethod
    def list_with_filters(cls, user_id: int,
                          project_id: Optional[int] = None,
                          status: Optional[str] = None,
                          status_list: Optional[List[str]] = None,
                          priority: Optional[str] = None,
                          begin_start: int = 0, begin_end: int = 0,
                          sort: str = "create_time_desc",
                          offset: int = 0, limit: int = 50) -> List[TodoRecord]:
        order_map = {
            "create_time_desc": "create_time desc",
            "create_time_asc": "create_time asc",
            "begin_asc": "begin_time asc",
            "priority_asc": "priority asc",
            "status_asc": "status asc",
        }
        order = order_map.get(sort, "create_time desc")
        where, vars = cls._build_where(user_id, project_id=project_id,
                                       status=status, status_list=status_list,
                                       priority=priority,
                                       begin_start=begin_start,
                                       begin_end=begin_end)
        rows = _todo_db.select(where=where, vars=vars, offset=offset,
                               limit=limit, order=order)
        return TodoRecord.from_dict_list(rows)

    @classmethod
    def count_by_project(cls, user_id: int, project_id: int,
                         is_deleted: int = 0) -> int:
        where, vars = cls._build_where(user_id, project_id=project_id,
                                       is_deleted=is_deleted)
        return _todo_db.count(where=where, vars=vars)

    @classmethod
    def count_by_status(cls, user_id: int, status: str,
                        is_deleted: int = 0) -> int:
        where, vars = cls._build_where(user_id, status=status,
                                       is_deleted=is_deleted)
        return _todo_db.count(where=where, vars=vars)

    @classmethod
    def count_with_filters(cls, user_id: int,
                           project_id: Optional[int] = None,
                           status: Optional[str] = None,
                           status_list: Optional[List[str]] = None,
                           priority: Optional[str] = None,
                           begin_start: int = 0, begin_end: int = 0,
                           is_deleted: int = 0) -> int:
        where, vars = cls._build_where(user_id, project_id=project_id,
                                       status=status, status_list=status_list,
                                       priority=priority,
                                       begin_start=begin_start,
                                       begin_end=begin_end,
                                       is_deleted=is_deleted)
        return _todo_db.count(where=where, vars=vars)

    @classmethod
    def count_group_by_project(cls, user_id: int,
                               is_deleted: int = 0) -> Dict[int, Dict[str, int]]:
        """按项目+状态分组统计，返回 {project_id: {status: count}}（一次查询）"""
        rows = _todo_db.select(
            what="project_id, status, COUNT(1) AS amount",
            where="user_id=$user_id AND is_deleted=$is_deleted",
            vars=dict(user_id=user_id, is_deleted=is_deleted),
            group="project_id, status")
        result = {}  # type: Dict[int, Dict[str, int]]
        for row in rows:
            project_id = int(row["project_id"])
            result.setdefault(project_id, {})[row["status"]] = int(row["amount"])
        return result

    # ---------- 迁移辅助 ----------

    @classmethod
    def reassign_project(cls, user_id: int, from_project_id: int, to_project_id: int) -> int:
        """把某用户未删除的待办从 from_project_id 批量改挂到 to_project_id"""
        return _todo_db.update(
            where="user_id=$user_id AND project_id=$project_id AND is_deleted=0",
            vars=dict(user_id=user_id, project_id=from_project_id),
            project_id=to_project_id)


class ProjectDao:
    """项目数据访问"""

    @classmethod
    def create(cls, project: ProjectRecord) -> int:
        now = dateutil.timestamp_ms()
        project.create_time = now
        project.update_time = now
        return _project_db.insert_record(project)

    @classmethod
    def get_by_id(cls, project_id: int, user_id: int = 0) -> Optional[ProjectRecord]:
        row = _project_db.select_first(where=dict(project_id=project_id))
        project = ProjectRecord.from_dict_or_None(row)
        if project is None:
            return None
        if user_id != 0 and project.user_id != user_id:
            return None
        return project

    @classmethod
    def get_by_name(cls, user_id: int, name: str) -> Optional[ProjectRecord]:
        row = _project_db.select_first(where=dict(user_id=user_id, name=name))
        return ProjectRecord.from_dict_or_None(row)

    @classmethod
    def get_or_create(cls, user_id: int, name: str) -> ProjectRecord:
        project = cls.get_by_name(user_id, name)
        if project is not None:
            return project
        project = ProjectRecord()
        project.user_id = user_id
        project.name = name
        project.project_id = cls.create(project)
        return project

    @classmethod
    def update(cls, project: ProjectRecord) -> int:
        project.update_time = dateutil.timestamp_ms()
        save = project.to_save_dict()
        save.pop("project_id", None)
        return _project_db.update(where=dict(project_id=project.project_id), **save)

    @classmethod
    def delete(cls, project_id: int, user_id: int = 0) -> int:
        """软删除：归档"""
        return _project_db.update(where=dict(project_id=project_id, user_id=user_id),
                                  status=ProjectStatusEnum.archived.value,
                                  update_time=dateutil.timestamp_ms())

    @classmethod
    def list_by_user(cls, user_id: int,
                     status: str = ProjectStatusEnum.active.value,
                     offset: int = 0, limit: int = 100) -> List[ProjectRecord]:
        where = "user_id=$user_id"
        vars = dict(user_id=user_id)  # type: Dict[str, Any]
        if status != "":
            where += " AND status=$status"
            vars["status"] = status
        rows = _project_db.select(where=where, vars=vars, offset=offset,
                                  limit=limit, order="create_time asc")
        return ProjectRecord.from_dict_list(rows)

    @classmethod
    def count_by_user(cls, user_id: int,
                      status: str = ProjectStatusEnum.active.value) -> int:
        where = "user_id=$user_id"
        vars = dict(user_id=user_id)  # type: Dict[str, Any]
        if status != "":
            where += " AND status=$status"
            vars["status"] = status
        return _project_db.count(where=where, vars=vars)
