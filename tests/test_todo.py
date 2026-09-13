# encoding=utf-8
import unittest

from tests.test_base import BaseTestCase

from xnote.core import xtables
from xnote_handlers.todo.dao import TodoDao, ProjectDao
from xnote_handlers.todo.todo_model import TodoRecord, TodoStatusEnum, TodoPriorityEnum
from xnote_handlers.todo.project_model import ProjectRecord, ProjectStatusEnum
from xnote_handlers.todo.todo_comment import to_comment_target_id
from xnote_handlers.note import dao_comment


def _clear_table(name):
    table = xtables.get_table_by_name(name)
    pk = "task_id" if name == "todo_task" else "project_id"
    for row in table.iter():
        table.delete(where={pk: row[pk]})


class TestTodoDao(BaseTestCase):

    def setUp(self):
        # 启动时的迁移可能已写入基线数据，清理以保证计数干净
        _clear_table("todo_task")
        _clear_table("todo_project")

    def test_crud(self):
        todo = TodoRecord()
        todo.user = "admin"
        todo.user_id = 1
        todo.content = "买牛奶"
        todo.priority = TodoPriorityEnum.high.value
        tid = TodoDao.create(todo)
        self.assertTrue(tid > 0)

        got = TodoDao.get_by_id(tid, user_id=1)
        self.assertIsNotNone(got)
        self.assertEqual(got.content, "买牛奶")
        self.assertEqual(got.priority, "high")

        # 用户越权访问应返回 None
        self.assertIsNone(TodoDao.get_by_id(tid, user_id=999))

        # 更新状态
        TodoDao.update_status(tid, TodoStatusEnum.done.value, user_id=1)
        self.assertEqual(TodoDao.get_by_id(tid).status, "done")
        self.assertTrue(TodoDao.get_by_id(tid).done_time > 0)

        # 软删除
        TodoDao.delete(tid, user_id=1)
        self.assertEqual(TodoDao.get_by_id(tid).is_deleted, 1)
        self.assertEqual(TodoDao.count_by_status(1, "done", is_deleted=0), 0)

    def test_queries(self):
        user_id = 1
        TodoDao.create(self._make(user_id, "t1", "done", "high", 0))
        TodoDao.create(self._make(user_id, "t2", "not_started", "low", 0))
        TodoDao.create(self._make(user_id, "t3", "done", "normal", 7))

        self.assertEqual(len(TodoDao.list_by_status(user_id, "done")), 2)
        self.assertEqual(len(TodoDao.list_by_priority(user_id, "high")), 1)
        self.assertEqual(TodoDao.count_by_project(user_id, 7), 1)
        self.assertEqual(len(TodoDao.list_with_filters(user_id, status="done", sort="create_time_asc")), 2)

    def test_status_group_and_project_counts(self):
        user_id = 1
        project = ProjectRecord()
        project.user_id = user_id
        project.name = "统计项目"
        pid = ProjectDao.create(project)

        pending_status_list = [TodoStatusEnum.not_started.value, TodoStatusEnum.in_progress.value]
        TodoDao.create(self._make(user_id, "未开始", "not_started", "normal", pid))
        TodoDao.create(self._make(user_id, "进行中", "in_progress", "normal", pid))
        TodoDao.create(self._make(user_id, "已完成", "done", "normal", pid))
        TodoDao.create(self._make(user_id, "已取消", "canceled", "normal", pid))

        # 【待办】= 未开始 + 进行中
        pending = TodoDao.list_with_filters(user_id, project_id=pid, status_list=pending_status_list)
        self.assertEqual(len(pending), 2)
        self.assertEqual(TodoDao.count_with_filters(user_id, project_id=pid,
                                                    status_list=pending_status_list), 2)
        # 全部（不过滤）
        self.assertEqual(len(TodoDao.list_with_filters(user_id, project_id=pid)), 4)

        # 分组计数
        count_map = TodoDao.count_group_by_project(user_id)
        bucket = count_map.get(pid, {})
        self.assertEqual(bucket.get("not_started", 0) + bucket.get("in_progress", 0), 2)
        self.assertEqual(bucket.get("done", 0), 1)

    def test_project(self):
        user_id = 1
        p = ProjectRecord()
        p.user_id = user_id
        p.name = "项目A"
        pid = ProjectDao.create(p)
        self.assertTrue(pid > 0)

        got = ProjectDao.get_by_id(pid, user_id=user_id)
        self.assertEqual(got.name, "项目A")

        self.assertIsNotNone(ProjectDao.get_by_name(user_id, "项目A"))
        same = ProjectDao.get_or_create(user_id, "项目A")
        self.assertEqual(same.project_id, pid)

        TodoDao.create(self._make(user_id, "in project", "not_started", "normal", pid))
        self.assertEqual(TodoDao.count_by_project(user_id, pid), 1)

        ProjectDao.delete(pid, user_id=user_id)
        self.assertEqual(ProjectDao.get_by_id(pid).status, "archived")

    def _make(self, user_id, content, status, priority, project_id):
        todo = TodoRecord()
        todo.user = "admin"
        todo.user_id = user_id
        todo.content = content
        todo.status = status
        todo.priority = priority
        todo.project_id = project_id
        return todo


class TestTodoCommentCount(BaseTestCase):
    """评论数量维护到 todo_task.comment_count 并在列表行展示"""

    def setUp(self):
        _clear_table("todo_task")

    def tearDown(self):
        _clear_table("todo_task")

    def _create(self):
        todo = TodoRecord()
        todo.user = "admin"
        todo.user_id = 1
        todo.content = "待办A"
        todo.status = TodoStatusEnum.not_started.value
        todo.priority = TodoPriorityEnum.normal.value
        todo.project_id = 0
        todo_id = TodoDao.create(todo)
        return todo_id

    def test_comment_count_on_save_and_delete(self):
        todo_id = self._create()
        target_id = to_comment_target_id(todo_id)

        # 发表评论，comment_count 自增
        self.json_request_return_dict(
            "/todo/comment/save", method="POST",
            data=dict(note_id=target_id, content="评论1"))
        todo = TodoDao.get_by_id(todo_id)
        self.assertEqual(todo.comment_count, 1)

        # 再发一条，comment_count = 2
        self.json_request_return_dict(
            "/todo/comment/save", method="POST",
            data=dict(note_id=target_id, content="评论2"))
        self.assertEqual(TodoDao.get_by_id(todo_id).comment_count, 2)

        # 删除一条，comment_count 回到 1
        comments, _ = dao_comment.list_parent_comments(
            target_id, limit=100, type="todo_task")
        self.json_request_return_dict(
            "/todo/comment/delete", method="POST",
            data=dict(comment_id=comments[0].id))
        self.assertEqual(TodoDao.get_by_id(todo_id).comment_count, 1)

    def test_comment_link_shows_count_on_list(self):
        todo_id = self._create()
        target_id = to_comment_target_id(todo_id)
        self.json_request_return_dict(
            "/todo/comment/save", method="POST",
            data=dict(note_id=target_id, content="评论1"))

        body = self.request_app("/todo?project_id=0").data.decode("utf-8")
        self.assertIn("评论(1)", body)

        # 无评论时只显示「评论」
        self.assertEqual(TodoDao.get_by_id(todo_id).comment_count, 1)
        TodoDao.update_comment_count(todo_id, 0)
        body2 = self.request_app("/todo?project_id=0").data.decode("utf-8")
        self.assertIn(">评论</a>", body2)

    def test_mine_page_todo_source_truncated(self):
        from xutils import textutil
        long_content = "这是一条非常非常非常非常非常非常非常非常长的待办任务标题需要被截断处理"
        todo = TodoRecord()
        todo.user = "admin"
        todo.user_id = 1
        todo.content = long_content
        todo.status = TodoStatusEnum.not_started.value
        todo.priority = TodoPriorityEnum.normal.value
        todo.project_id = 0
        todo_id = TodoDao.create(todo)

        target_id = to_comment_target_id(todo_id)
        self.json_request_return_dict(
            "/todo/comment/save", method="POST",
            data=dict(note_id=target_id, content="我的评论"))

        # 我的评论页通过 /note/comments(list_type=user) 异步加载，来源应指向待办详情
        body = self.request_app(
            "/note/comments?list_type=user&show_note=true&resp_type=html"
        ).data.decode("utf-8")

        self.assertIn("/todo/detail?task_id=%s" % todo_id, body)
        # 长名称被截断，完整内容放在 title 上供 hover 查看
        self.assertIn("title=\"%s\"" % long_content, body)
        self.assertIn(textutil.get_short_text(long_content, 20), body)
        # 可见的来源文本是截断后的，而非完整长名称
        self.assertNotEqual(long_content, textutil.get_short_text(long_content, 20))

    def test_list_row_has_detail_link(self):
        todo_id = self._create()
        body = self.request_app("/todo?project_id=0").data.decode("utf-8")
        self.assertIn("/todo/detail?task_id=%s" % todo_id, body)
        self.assertIn('class="todo-detail-link"', body)

    def test_detail_page_has_comment_list(self):
        todo_id = self._create()
        body = self.request_app(
            "/todo/detail?task_id=%s" % todo_id).data.decode("utf-8")
        # 详情页复用了评论组件（列表/保存均走 todo 评论端点）
        self.assertIn("/todo/comment/list", body)
        self.assertIn("todo_task", body)


if __name__ == "__main__":
    unittest.main()
