# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2026/09/12
# 把旧的待办消息(task/done)迁移到新的 todo 表
import logging

from . import base

from xnote.core import xauth, xtables
from xnote_handlers.message.dao import MsgIndexDao, MessageDao
from xnote_handlers.message.message_model import MsgIndex
from xnote_handlers.todo.dao import TodoDao, ProjectDao
from xnote_handlers.todo.todo_model import (
    TodoRecord, TodoStatusEnum, TodoPriorityEnum, parse_time_ms)
from xnote_handlers.todo.project_model import DEFAULT_PROJECT_NAME


# 迁移时每批处理的数量（数据量可能很大，分批遍历避免一次性加载）
BATCH_SIZE = 1000


def do_upgrade():
    # 待办表由 todo_project/todo_todo 进一步重命名为 todo_project/todo_task，
    # 且主键改名为 project_id/task_id。因尚未正式发布，用全新 key 重新执行迁移，
    # 把消息按 msg_id 作为主键写入新表 todo_task（幂等，可安全重试）。
    base.execute_upgrade("20260912_todo_task_from_message", migrate_message_todo)
    # 迁移完成后，把未分类待办(project_id=0)关联到默认项目
    base.execute_upgrade("20260912_default_project", migrate_default_project)


def migrate_default_project():
    """为存在未分类待办(project_id=0)的用户创建默认项目，并把这些待办关联过去

    用户量可能很大，这里用 xauth.iter_user 分批遍历（只对有未分类待办的用户建默认项目）。
    """
    users = 0
    moved = 0
    for user_info in xauth.iter_user(limit=-1):
        if TodoDao.count_by_project(user_info.id, 0) == 0:
            continue
        project = ProjectDao.get_or_create(user_info.id, DEFAULT_PROJECT_NAME)
        moved += TodoDao.reassign_project(user_info.id, 0, project.project_id)
        users += 1
    logging.info("migrate_default_project done, users=%d, moved=%d", users, moved)


def migrate_message_todo(batch_size: int = BATCH_SIZE):
    """把 msg_index 中 tag 为 task/done 的消息迁移为 todo 记录（增量复制，不改原数据）

    以消息ID(msg_id)作为待办的 task_id，迁移前先判断是否已存在，
    这样迁移中途失败后重试不会产生重复数据（幂等）。
    消息量可能很大，这里用 table_proxy.iter 按主键分批遍历，避免 offset 翻页。
    """
    migrated = 0
    index_db = xtables.get_table_by_name("msg_index")
    where = " AND tag in $tag_list"
    vars = dict(tag_list=["task", "done"])

    for item in index_db.iter(where=where, vars=vars, batch_size=batch_size):
        index = MsgIndex.from_dict(item)
        # 幂等：task_id 就是 msg_id，已迁移过则跳过
        if TodoDao.get_by_id(index.id) is not None:
            continue

        msg = MessageDao.get_by_int_id(index.id)
        if msg is None:
            continue

        todo = TodoRecord()
        todo.user = index.user_name
        todo.user_id = index.user_id
        todo.content = msg.content or ""
        if index.tag == "done":
            todo.status = TodoStatusEnum.done.value
            todo.done_time = parse_time_ms(index.change_time)
        else:
            todo.status = TodoStatusEnum.not_started.value
            todo.done_time = 0
        todo.priority = TodoPriorityEnum.normal.value
        todo.project_id = 0
        # 保留原消息的创建/更新时间（为空时由 create_with_id 补当前时间）
        todo.create_time = parse_time_ms(index.ctime)
        todo.update_time = parse_time_ms(index.mtime)
        TodoDao.create_with_id(todo, index.id)
        migrated += 1

    # 数量校验（不一致仅告警，不阻断启动）
    old_task = MsgIndexDao.count(user_id=0, tag="task")
    old_done = MsgIndexDao.count(user_id=0, tag="done")
    new_count = _todo_db_count()
    if new_count != old_task + old_done:
        logging.warning("todo 迁移数量不一致: new=%s, old_task=%s, old_done=%s",
                        new_count, old_task, old_done)
    logging.info("migrate_message_todo done, migrated=%d", migrated)


def _todo_db_count():
    db = xtables.get_table_by_name("todo_task")
    return db.count(where="1=1")
