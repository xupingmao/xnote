# encoding=utf-8
import unittest

from tests.test_base import BaseTestCase

from xnote.core import xauth, xtables
from xnote_handlers.message.dao import MsgIndexDao
from xnote_handlers.message.message_model import MessageDO
from xnote_handlers.message import dao as msg_dao

from xnote_migrate.upgrade_024 import migrate_message_todo, migrate_default_project
from xnote_migrate.base import SystemUpgradeLogDao
from xnote_handlers.todo.dao import TodoDao, ProjectDao
from xnote_handlers.todo.todo_model import TodoRecord, TodoStatusEnum, parse_time_ms
from xnote_handlers.todo.project_model import DEFAULT_PROJECT_NAME


class TestTodoMigrate(BaseTestCase):

    def _seed_message(self, tag, content, user="admin"):
        msg = MessageDO()
        msg.user = user
        msg.tag = tag
        msg.content = content
        msg.ctime = "2026-09-01 10:00:00"
        return msg_dao.create_message(msg)

    def test_migrate_task_and_done(self):
        # 迁移按消息的真实 user_id 写入 todo，这里统一用 admin 的 user_id 做自洽校验
        user_id = xauth.UserDao.get_id_by_name("admin")
        self.assertNotEqual(user_id, 0)

        # 清理已有 todo，保证计数干净（启动时的迁移可能已写入基线数据）
        db = __import__("xnote.core.xtables", fromlist=["get_table_by_name"])
        todo_table = db.get_table_by_name("todo_task")
        for row in todo_table.iter():
            todo_table.delete(where=dict(task_id=row["task_id"]))

        # 记录 admin 基线消息数量
        base_task = MsgIndexDao.count(user_id=user_id, tag="task")
        base_done = MsgIndexDao.count(user_id=user_id, tag="done")

        # 种子数据：3 个 task + 2 个 done
        self._seed_message("task", "任务A-migrate")
        self._seed_message("task", "任务B-migrate")
        self._seed_message("task", "任务C-migrate")
        self._seed_message("done", "已完成A-migrate")
        self._seed_message("done", "已完成B-migrate")

        after_task = MsgIndexDao.count(user_id=user_id, tag="task")
        after_done = MsgIndexDao.count(user_id=user_id, tag="done")
        self.assertEqual(after_task, base_task + 3)
        self.assertEqual(after_done, base_done + 2)

        # 清掉幂等守卫，使本次迁移逻辑可重复执行（测试用）
        SystemUpgradeLogDao.delete("20260912_todo_task_from_message")
        migrate_message_todo()

        # admin 的 todo 总数 = admin 的 task + done 消息数
        self.assertEqual(TodoDao.count_with_filters(user_id),
                         after_task + after_done)

        # 字段映射：种子数据
        not_started = TodoDao.list_by_status(user_id,
                                             TodoStatusEnum.not_started.value)
        done_todos = TodoDao.list_by_status(user_id,
                                           TodoStatusEnum.done.value)

        started_contents = [t.content for t in not_started]
        done_contents = [t.content for t in done_todos]
        for c in ["任务A-migrate", "任务B-migrate", "任务C-migrate"]:
            self.assertIn(c, started_contents)
        for c in ["已完成A-migrate", "已完成B-migrate"]:
            self.assertIn(c, done_contents)

        for t in done_todos:
            if "migrate" in t.content:
                self.assertTrue(t.done_time > 0)

    def test_migrate_create_and_update_time(self):
        """迁移时保留原消息的创建时间/更新时间"""
        todo_table = xtables.get_table_by_name("todo_task")
        for row in todo_table.iter():
            todo_table.delete(where=dict(task_id=row["task_id"]))

        # ctime 作为创建时间，mtime 作为更新时间
        msg_id = self._seed_message("task", "时间迁移待办")
        MsgIndexDao.update_tag(msg_id, tag="task", update_time="2026-09-02 11:22:33")

        SystemUpgradeLogDao.delete("20260912_todo_task_from_message")
        migrate_message_todo()

        todo = TodoDao.get_by_id(msg_id)
        self.assertIsNotNone(todo)
        self.assertEqual(todo.create_time, parse_time_ms("2026-09-01 10:00:00"))
        self.assertEqual(todo.update_time, parse_time_ms("2026-09-02 11:22:33"))

    def test_default_project_migration(self):
        user_id = xauth.UserDao.get_id_by_name("admin")
        todo_table = xtables.get_table_by_name("todo_task")
        # 清空待办，造一条未分类待办
        for row in todo_table.iter():
            todo_table.delete(where=dict(task_id=row["task_id"]))

        todo = TodoRecord()
        todo.user = "admin"
        todo.user_id = user_id
        todo.content = "未分类待办-migrate"
        todo.project_id = 0
        todo_id = TodoDao.create(todo)

        self.assertEqual(TodoDao.get_by_id(todo_id).project_id, 0)

        # 重跑迁移
        SystemUpgradeLogDao.delete("20260912_default_project")
        migrate_default_project()

        moved = TodoDao.get_by_id(todo_id)
        self.assertNotEqual(moved.project_id, 0)
        project = ProjectDao.get_by_id(moved.project_id)
        self.assertIsNotNone(project)
        self.assertEqual(project.name, DEFAULT_PROJECT_NAME)
        # 没有残留的未分类待办
        self.assertEqual(TodoDao.count_by_project(user_id, 0), 0)

    def test_migrate_multi_batch(self):
        """数据量大时按主键分批遍历，跨批次的数据也要全部迁移"""
        todo_table = xtables.get_table_by_name("todo_task")
        for row in todo_table.iter():
            todo_table.delete(where=dict(task_id=row["task_id"]))

        msg_ids = []
        for index in range(3):
            msg_ids.append(self._seed_message("task", "分批待办%d-migrate" % index))

        SystemUpgradeLogDao.delete("20260912_todo_task_from_message")
        # 批次大小设为 1，强制走多批次
        migrate_message_todo(batch_size=1)

        for index, msg_id in enumerate(msg_ids):
            todo = TodoDao.get_by_id(msg_id)
            self.assertIsNotNone(todo)
            self.assertEqual(todo.content, "分批待办%d-migrate" % index)

    def test_migrate_idempotent(self):
        """以 msg_id 作为 task_id，重复迁移不产生重复数据"""
        user_id = xauth.UserDao.get_id_by_name("admin")
        todo_table = xtables.get_table_by_name("todo_task")
        for row in todo_table.iter():
            todo_table.delete(where=dict(task_id=row["task_id"]))

        msg_id = self._seed_message("task", "幂等待办-migrate")
        SystemUpgradeLogDao.delete("20260912_todo_task_from_message")

        migrate_message_todo()
        # task_id 就是消息ID
        todo = TodoDao.get_by_id(msg_id)
        self.assertIsNotNone(todo)
        self.assertEqual(todo.content, "幂等待办-migrate")
        count1 = TodoDao.count_with_filters(user_id)

        # 再次执行（模拟失败重试）不产生重复
        migrate_message_todo()
        count2 = TodoDao.count_with_filters(user_id)
        self.assertEqual(count1, count2)


if __name__ == "__main__":
    unittest.main()
