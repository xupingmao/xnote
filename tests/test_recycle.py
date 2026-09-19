# encoding=utf-8
import unittest

from tests.test_base import BaseTestCase

from xnote.service import recycle_service
from xnote.service.recycle_service import RecycleService


def _clear_table():
    table = recycle_service.get_table()
    for row in table.iter():
        table.delete(where=dict(id=row["id"]))


class TestRecycleService(BaseTestCase):

    def setUp(self):
        _clear_table()

    def _add(self, record_id=1, content=None, user_id=1, **kw):
        if content is None:
            content = {"task_id": record_id, "content": "待办-%s" % record_id}
        return RecycleService.add("todo_task", record_id, content,
                              user_id=user_id,
                              summary=content.get("content", ""),
                              **kw)

    def test_add_and_get(self):
        id = self._add(record_id=11)
        record = RecycleService.get_by_id(id)
        assert record is not None
        self.assertEqual(record.table_name, "todo_task")
        self.assertEqual(record.record_id, 11)
        self.assertEqual(record.user_id, 1)
        self.assertEqual(record.get_content_dict()["content"], "待办-11")
        self.assertEqual(record.summary, "待办-11")
        self.assertEqual(record.operator_id, 1)
        self.assertFalse(record.is_restored())
        self.assertTrue(record.create_time > 0)

    def test_add_with_data_record(self):
        from xnote_handlers.todo.todo_model import TodoRecord

        todo = TodoRecord()
        todo.task_id = 12
        todo.content = "来自模型的待办"

        id = RecycleService.add("todo_task", 12, todo, user_id=2)
        record = RecycleService.get_by_id(id)

        assert record is not None
        content = record.get_content_dict()
        self.assertEqual(content["content"], "来自模型的待办")
        self.assertEqual(record.user_id, 2)

    def test_list_and_count(self):
        self._add(record_id=1)
        self._add(record_id=2)
        self._add(record_id=3, content={"content": "别人的待办"}, user_id=9)

        self.assertEqual(RecycleService.count(user_id=1), 2)
        self.assertEqual(RecycleService.count(), 3)

        # 按删除时间倒序
        records = RecycleService.list(user_id=1)
        self.assertEqual(len(records), 2)
        self.assertTrue(records[0].create_time >= records[1].create_time)

        # 按表过滤
        self.assertEqual(RecycleService.count(table_name="todo_task"), 3)
        self.assertEqual(RecycleService.count(table_name="note_index"), 0)

        # 按摘要搜索
        self.assertEqual(RecycleService.count(key="别人的"), 1)

    def test_restore(self):
        id = self._add(record_id=21)
        content = RecycleService.restore(id, user_id=1)

        assert content is not None
        self.assertEqual(content["content"], "待办-21")

        record = RecycleService.get_by_id(id)
        assert record is not None
        self.assertTrue(record.is_restored())
        self.assertEqual(record.restore_user_id, 1)

        # 重复恢复返回None
        self.assertIsNone(RecycleService.restore(id, user_id=1))

        # 已恢复的不再出现在未恢复列表里
        self.assertEqual(RecycleService.count(restored=False), 0)
        self.assertEqual(RecycleService.count(restored=True), 1)

    def test_delete(self):
        id = self._add(record_id=31)
        RecycleService.delete(id)
        self.assertIsNone(RecycleService.get_by_id(id))
        self.assertEqual(RecycleService.count(), 0)

    def test_clean_before_time(self):
        self._add(record_id=41)
        self._add(record_id=42)

        # 清理未来时间点之前的数据, 全部删除
        import time
        deleted = RecycleService.clean_before_time(int(time.time() * 1000) + 10000)
        self.assertEqual(deleted, 2)
        self.assertEqual(RecycleService.count(), 0)

    def test_extra(self):
        id = self._add(record_id=51, extra={"reason": "用户主动删除"})
        record = RecycleService.get_by_id(id)
        assert record is not None
        self.assertEqual(record.get_extra_dict()["reason"], "用户主动删除")


if __name__ == "__main__":
    unittest.main()
