# encoding=utf-8
import json
import unittest

from tests.test_base import BaseTestCase

from xnote_handlers.todo.todo_comment import to_comment_target_id
from xnote_handlers.note import dao_comment


class TestTodoApi(BaseTestCase):

    def test_create_and_list(self):
        resp = self.json_request_return_dict(
            "/api/todo/create", method="POST",
            data=dict(content="买牛奶", priority="high"))
        self.assertTrue(resp["success"])
        new_id = resp["data"]
        self.assertTrue(new_id > 0)

        lst = self.json_request_return_dict("/api/todo/list?status=not_started")
        self.assertTrue(lst["success"])
        self.assertGreaterEqual(lst["data"]["total"], 1)
        ids = [item["task_id"] for item in lst["data"]["items"]]
        self.assertIn(new_id, ids)

    def test_status_finish(self):
        resp = self.json_request_return_dict(
            "/api/todo/create", method="POST", data=dict(content="写报告"))
        todo_id = resp["data"]

        resp = self.json_request_return_dict(
            "/api/todo/status", method="POST",
            data=dict(task_id=todo_id, action="finish"))
        self.assertTrue(resp["success"])
        self.assertEqual(resp["data"]["status"], "done")

    def test_update_and_delete(self):
        resp = self.json_request_return_dict(
            "/api/todo/create", method="POST", data=dict(content="临时任务"))
        todo_id = resp["data"]

        resp = self.json_request_return_dict(
            "/api/todo/update", method="POST",
            data=dict(task_id=todo_id, content="临时任务改", priority="urgent"))
        self.assertTrue(resp["success"])

        lst = self.json_request_return_dict("/api/todo/list")
        found = [item for item in lst["data"]["items"] if item["task_id"] == todo_id][0]
        self.assertEqual(found["content"], "临时任务改")
        self.assertEqual(found["priority"], "urgent")

        resp = self.json_request_return_dict(
            "/api/todo/delete", method="POST", data=dict(task_id=todo_id))
        self.assertTrue(resp["success"])

    def test_project_crud(self):
        resp = self.json_request_return_dict(
            "/api/project/create", method="POST", data=dict(name="项目X"))
        self.assertTrue(resp["success"])
        pid = resp["data"]
        self.assertTrue(pid > 0)

        lst = self.json_request_return_dict("/api/project/list")
        self.assertTrue(lst["success"])
        names = [item["name"] for item in lst["data"]]
        self.assertIn("项目X", names)


class TestTodoPages(BaseTestCase):
    """页面渲染冒烟测试(HTML 路径，API 测试未覆盖)"""

    def test_todo_home_page(self):
        # 首页是项目列表(ListView)
        self.json_request_return_dict("/api/project/create", method="POST",
                                      data=dict(name="首页项目"))
        resp = self.request_app("/todo")
        self.assertEqual("200 OK", resp.status)
        body = resp.data.decode("utf-8")
        self.assertIn("新建项目", body)
        self.assertIn("list-item", body)

    def test_todo_list_page(self):
        # 指定项目时展示该项目的待办列表(ListView)
        self.json_request_return_dict("/api/todo/create", method="POST",
                                      data=dict(content="列表页待办", project_id="1"))
        resp = self.request_app("/todo?project_id=1")
        self.assertEqual("200 OK", resp.status)
        body = resp.data.decode("utf-8")
        self.assertIn("新建待办", body)
        self.assertIn("x-tab-box", body)
        self.assertIn("list-item", body)

    def test_todo_list_page_with_filter(self):
        resp = self.request_app("/todo?project_id=1&status=not_started&priority=high")
        self.assertEqual("200 OK", resp.status)

    def test_todo_list_default_filter(self):
        # 默认【待办】Tab，且包含 待办/全部/未开始/进行中/完成/取消
        self.json_request_return_dict("/api/todo/create", method="POST",
                                      data=dict(content="默认筛选待办", project_id="1"))
        body = self.request_app("/todo?project_id=1").data.decode("utf-8")
        self.assertIn('data-tab-default="pending"', body)
        self.assertIn('data-tab-value="pending"', body)
        self.assertIn('data-tab-value="all"', body)
        self.assertIn('data-tab-value="not_started"', body)
        self.assertIn('data-tab-value="in_progress"', body)
        self.assertIn('data-tab-value="done"', body)
        self.assertIn('data-tab-value="canceled"', body)

    def test_project_pending_done_counts(self):
        pid = self.json_request_return_dict("/api/project/create", method="POST",
                                            data=dict(name="计数页面项目"))["data"]
        self.json_request_return_dict("/api/todo/create", method="POST",
                                      data=dict(content="计数待办", project_id=str(pid)))
        body = self.request_app("/todo").data.decode("utf-8")
        idx = body.find("计数页面项目")
        self.assertGreater(idx, 0)
        row = body[idx:idx + 400]
        self.assertIn("待办 1", row)
        self.assertIn("完成 0", row)

    def test_todo_pagination(self):
        pid = self.json_request_return_dict("/api/project/create", method="POST",
                                            data=dict(name="分页测试项目"))["data"]
        for i in range(51):
            self.json_request_return_dict("/api/todo/create", method="POST",
                                          data=dict(content="分页%02d" % i, project_id=str(pid)))
        p1 = self.request_app("/todo?project_id=%s" % pid).data.decode("utf-8")
        self.assertIn("pagenation", p1)
        self.assertEqual(p1.count('class="list-item "'), 50)
        self.assertIn("page=2", p1)

        p2 = self.request_app("/todo?project_id=%s&page=2" % pid).data.decode("utf-8")
        self.assertEqual(p2.count('class="list-item "'), 1)

    def test_todo_edit_form(self):
        # 新建待办的编辑表单（ajax 局部渲染）
        resp = self.request_app("/todo?action=edit&model=task&project_id=1")
        self.assertEqual("200 OK", resp.status)
        body = resp.data.decode("utf-8")
        self.assertIn('name="content"', body)
        self.assertIn("<textarea", body)  # 内容使用 textarea
        # 所属项目可选
        self.assertIn('name="project_id"', body)
        self.assertIn("<select", body)
        # 完成时间只读展示
        self.assertIn("完成时间", body)
        self.assertRegex(body, r'name="done_time"[^>]*readonly')


class TestTodoForm(BaseTestCase):
    """页面插件表单流程测试(创建/状态变更/移动/删除)"""

    def _post_form(self, url, **fields):
        return self.json_request_return_dict(url, method="POST",
                                             data=dict(data=json.dumps(fields)))

    def test_create_task_via_form(self):
        resp = self._post_form("/todo?action=save&model=task",
                               project_id="1", content="表单待办",
                               priority="high", begin_time="", end_time="")
        self.assertTrue(resp["success"])

        lst = self.json_request_return_dict("/api/todo/list?project_id=1")
        contents = [item["content"] for item in lst["data"]["items"]]
        self.assertIn("表单待办", contents)

    def test_create_project_via_form(self):
        resp = self._post_form("/todo?action=save&model=project",
                               name="表单项目", desc="来自表单")
        self.assertTrue(resp["success"])

        lst = self.json_request_return_dict("/api/project/list")
        names = [item["name"] for item in lst["data"]]
        self.assertIn("表单项目", names)

    def test_project_status_via_form(self):
        # 项目编辑表单包含状态字段
        form_body = self.request_app("/todo?action=edit&model=project").data.decode("utf-8")
        self.assertIn('name="status"', form_body)

        # 新建一个已归档项目
        resp = self._post_form("/todo?action=save&model=project",
                               name="归档项目", desc="", status="archived")
        self.assertTrue(resp["success"])

        # 默认(进行中)列表查不到，归档列表能查到
        active_names = [item["name"] for item in
                        self.json_request_return_dict("/api/project/list")["data"]]
        self.assertNotIn("归档项目", active_names)
        archived_names = [item["name"] for item in
                          self.json_request_return_dict("/api/project/list?status=archived")["data"]]
        self.assertIn("归档项目", archived_names)

    def test_status_and_delete_via_form(self):
        self._post_form("/todo?action=save&model=task",
                        project_id="1", content="待完成", priority="normal",
                        begin_time="", end_time="")
        lst = self.json_request_return_dict("/api/todo/list?project_id=1")
        task = [item for item in lst["data"]["items"] if item["content"] == "待完成"][0]
        task_id = task["task_id"]

        # 完成
        resp = self.json_request_return_dict(
            "/todo?action=finish&model=task&project_id=1&task_id=%s" % task_id)
        self.assertTrue(resp["success"])
        lst2 = self.json_request_return_dict("/api/todo/list?project_id=1")
        found = [item for item in lst2["data"]["items"] if item["task_id"] == task_id][0]
        self.assertEqual(found["status"], "done")

        # 删除
        resp = self.json_request_return_dict(
            "/todo?action=delete&model=task&project_id=1&task_id=%s" % task_id)
        self.assertTrue(resp["success"])

    def test_reopen_canceled_task(self):
        self._post_form("/todo?action=save&model=task",
                        project_id="1", content="取消后重开", priority="normal",
                        begin_time="", end_time="")
        lst = self.json_request_return_dict("/api/todo/list?project_id=1")
        task_id = [item for item in lst["data"]["items"]
                   if item["content"] == "取消后重开"][0]["task_id"]

        # 取消
        resp = self.json_request_return_dict(
            "/todo?action=cancel&model=task&project_id=1&task_id=%s" % task_id)
        self.assertTrue(resp["success"])

        # 已取消的任务在【全部】视图仍提供【重开】入口，且状态变更不需要确认
        page = self.request_app("/todo?project_id=1&status=all").data.decode("utf-8")
        self.assertIn(
            "action=reset&amp;model=task&amp;project_id=1&amp;task_id=%s" % task_id, page)
        self.assertIn("xnote.table.handleAjaxAction(this)", page)
        self.assertIn("xnote.table.handleConfirmAction(this)", page)  # 删除仍然需要确认

        # 重开生效（回到未开始）
        resp = self.json_request_return_dict(
            "/todo?action=reset&model=task&project_id=1&task_id=%s" % task_id)
        self.assertTrue(resp["success"])
        lst2 = self.json_request_return_dict("/api/todo/list?project_id=1")
        found = [item for item in lst2["data"]["items"] if item["task_id"] == task_id][0]
        self.assertEqual(found["status"], "not_started")

    def test_move_task_project_via_form(self):
        # 建源/目标两个项目
        pid1 = self.json_request_return_dict(
            "/api/project/create", method="POST", data=dict(name="移动源"))["data"]
        pid2 = self.json_request_return_dict(
            "/api/project/create", method="POST", data=dict(name="移动目标"))["data"]

        # 在 pid1 下建待办
        self._post_form("/todo?action=save&model=task",
                        project_id=str(pid1), content="移动待办",
                        priority="normal", begin_time="", end_time="")
        lst = self.json_request_return_dict("/api/todo/list?project_id=%s" % pid1)
        task_id = [item for item in lst["data"]["items"]
                   if item["content"] == "移动待办"][0]["task_id"]

        # 通过编辑表单改到 pid2
        resp = self._post_form("/todo?action=save&model=task",
                               task_id=str(task_id), project_id=str(pid2),
                               content="移动待办", priority="normal",
                               begin_time="", end_time="")
        self.assertTrue(resp["success"])

        # pid2 下能查到，pid1 下查不到
        ids2 = [item["task_id"] for item in
                self.json_request_return_dict("/api/todo/list?project_id=%s" % pid2)["data"]["items"]]
        self.assertIn(task_id, ids2)
        ids1 = [item["task_id"] for item in
                self.json_request_return_dict("/api/todo/list?project_id=%s" % pid1)["data"]["items"]]
        self.assertNotIn(task_id, ids1)

    def _create_task(self, content, project_id="1"):
        self._post_form("/todo?action=save&model=task", project_id=str(project_id),
                        content=content, priority="normal", begin_time="2026-09-12", end_time="")
        lst = self.json_request_return_dict("/api/todo/list?project_id=%s" % project_id)
        return [item for item in lst["data"]["items"] if item["content"] == content][0]["task_id"]

    def test_todo_detail_page(self):
        task_id = self._create_task("# 详情页待办")
        resp = self.request_app("/todo/detail?task_id=%s" % task_id)
        self.assertEqual("200 OK", resp.status)
        body = resp.data.decode("utf-8")
        self.assertIn("详情页待办", body)     # 基础信息
        self.assertIn("card-title", body)    # 标题(base_title.html)
        self.assertIn('class="link2 path-link"', body)  # 面包屑(parent_link)
        self.assertIn("返回", body)
        # 内容使用 mark_text 处理（markdown -> h1）
        self.assertIn('<h1 class="block-title">详情页待办</h1>', body)
        self.assertIn("todo-detail-tags", body)  # 信息用标签展示
        self.assertIn("commentText", body)   # 评论输入框
        self.assertIn("/todo/comment/list", body)
        self.assertIn("/todo/comment/save", body)

    def test_todo_comment_flow(self):
        task_id = self._create_task("评论待办")
        target_id = to_comment_target_id(task_id)

        # 发表评论
        resp = self.json_request_return_dict(
            "/todo/comment/save", method="POST",
            data=dict(note_id=str(target_id), content="待办评论内容", type="todo_task"))
        self.assertTrue(resp["success"])

        # 列表能查到
        html = self.request_app(
            "/todo/comment/list?note_id=%s&resp_type=html" % target_id).data.decode("utf-8")
        self.assertIn("待办评论内容", html)

        # 隔离：同数字 id 的笔记视角查不到该评论（target_id 独立空间）
        note_comments, _ = dao_comment.list_parent_comments(task_id, type="")
        self.assertFalse(any(c.content == "待办评论内容" for c in note_comments))


if __name__ == "__main__":
    unittest.main()
