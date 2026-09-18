# encoding=utf-8
import json
import unittest

from xutils import quote
from tests.test_base import BaseTestCase
from xnote_handlers.comment import to_comment_target_id
from xnote_handlers.comment import dao_comment


class TestTodoApi(BaseTestCase):

    def test_create_and_list(self):
        resp = self.json_request_return_dict(
            "/api/v1/todo/create", method="POST",
            data=dict(content="买牛奶", priority="high"))
        self.assertTrue(resp["success"])
        new_id = resp["data"]
        self.assertTrue(new_id > 0)

        lst = self.json_request_return_dict("/api/v1/todo/list?status=not_started")
        self.assertTrue(lst["success"])
        self.assertGreaterEqual(lst["data"]["total"], 1)
        ids = [item["task_id"] for item in lst["data"]["items"]]
        self.assertIn(new_id, ids)

    def test_status_finish(self):
        resp = self.json_request_return_dict(
            "/api/v1/todo/create", method="POST", data=dict(content="写报告"))
        todo_id = resp["data"]

        resp = self.json_request_return_dict(
            "/api/v1/todo/status", method="POST",
            data=dict(task_id=todo_id, action="finish"))
        self.assertTrue(resp["success"])
        self.assertEqual(resp["data"]["status"], "done")

    def test_update_and_delete(self):
        resp = self.json_request_return_dict(
            "/api/v1/todo/create", method="POST", data=dict(content="临时任务"))
        todo_id = resp["data"]

        resp = self.json_request_return_dict(
            "/api/v1/todo/update", method="POST",
            data=dict(task_id=todo_id, content="临时任务改", priority="urgent"))
        self.assertTrue(resp["success"])

        lst = self.json_request_return_dict("/api/v1/todo/list")
        found = [item for item in lst["data"]["items"] if item["task_id"] == todo_id][0]
        self.assertEqual(found["content"], "临时任务改")
        self.assertEqual(found["priority"], "urgent")

        resp = self.json_request_return_dict(
            "/api/v1/todo/delete", method="POST", data=dict(task_id=todo_id))
        self.assertTrue(resp["success"])

    def test_project_crud(self):
        resp = self.json_request_return_dict(
            "/api/v1/project/create", method="POST", data=dict(name="项目X"))
        self.assertTrue(resp["success"])
        pid = resp["data"]
        self.assertTrue(pid > 0)

        lst = self.json_request_return_dict("/api/v1/project/list")
        self.assertTrue(lst["success"])
        names = [item["name"] for item in lst["data"]]
        self.assertIn("项目X", names)

    def test_search_by_key(self):
        # 用唯一内容隔离共享持久化测试库（其它用例/种子数据可能已有同类内容）
        import uuid
        marker = uuid.uuid4().hex
        meet = "会议%s" % marker
        fruit = "水果%s" % marker
        pid_resp = self.json_request_return_dict(
            "/api/v1/project/create", method="POST",
            data=dict(name="搜索键项目%s" % marker))
        self.assertTrue(pid_resp["success"])
        pid = pid_resp["data"]
        meet_resp = self.json_request_return_dict(
            "/api/v1/todo/create", method="POST",
            data=dict(content=meet, project_id=str(pid)))
        self.assertTrue(meet_resp["success"])
        fruit_resp = self.json_request_return_dict(
            "/api/v1/todo/create", method="POST",
            data=dict(content=fruit, project_id=str(pid)))
        self.assertTrue(fruit_resp["success"])

        # 按“会议”关键词搜索：只命中会议那条，不命中水果那条
        quoted_name = quote(meet)
        matched = self.json_request_return_dict(f"/api/v1/todo/list?key={quoted_name}")
        self.assertTrue(matched["success"])
        contents = [item["content"] for item in matched["data"]["items"]]
        self.assertEqual(contents, [meet])

        # 换“水果”关键词：只命中水果那条
        matched2 = self.json_request_return_dict("/api/v1/todo/list?key=" + quote(fruit))
        contents2 = [item["content"] for item in matched2["data"]["items"]]
        self.assertEqual(contents2, [fruit])


class TestTodoPages(BaseTestCase):
    """页面渲染冒烟测试(HTML 路径，API 测试未覆盖)"""

    def test_todo_home_page(self):
        # 首页是项目列表(ListView)
        self.json_request_return_dict("/api/v1/project/create", method="POST",
                                      data=dict(name="首页项目"))
        resp = self.request_app("/todo")
        self.assertEqual("200 OK", resp.status)
        body = resp.data.decode("utf-8")
        self.assertIn("新建项目", body)
        self.assertIn("list-item", body)

    def test_todo_list_page(self):
        # 指定项目时展示该项目的待办列表(ListView)
        self.json_request_return_dict("/api/v1/todo/create", method="POST",
                                      data=dict(content="列表页待办", project_id="1"))
        resp = self.request_app("/todo/task?project_id=1")
        self.assertEqual("200 OK", resp.status)
        body = resp.data.decode("utf-8")
        self.assertIn("新建待办", body)
        self.assertIn("x-tab-box", body)
        self.assertIn("list-item", body)

    def test_todo_list_title_uses_project_name(self):
        # 待办列表标题展示所属项目名称
        pid = self.json_request_return_dict("/api/v1/project/create", method="POST",
                                            data=dict(name="标题项目"))["data"]
        self.json_request_return_dict("/api/v1/todo/create", method="POST",
                                      data=dict(content="标题待办", project_id=str(pid)))
        body = self.request_app("/todo/task?project_id=%s" % pid).data.decode("utf-8")
        idx = body.find("card-title")
        self.assertGreater(idx, 0)
        self.assertIn("<span>标题项目</span>", body[idx:idx + 400])

    def test_todo_list_page_with_filter(self):
        resp = self.request_app("/todo/task?project_id=1&status=not_started&priority=high")
        self.assertEqual("200 OK", resp.status)

    def test_todo_list_content_uses_mark_text(self):
        # 列表行内容用 mark_text 渲染（markdown 语法生效），且内容后附【详情】入口
        tid = self.json_request_return_dict("/api/v1/todo/create", method="POST",
                                            data=dict(content="# 标题待办", project_id="1"))["data"]
        body = self.request_app("/todo/task?project_id=1").data.decode("utf-8")
        row = self._find_task_row(body)
        self.assertIsNotNone(row)
        # 内容按 markdown 渲染
        self.assertIn('<h1 class="block-title">标题待办</h1>', row)
        # 内容后附【详情】链接（进入详情页）
        self.assertIn('<a href="/todo/detail?task_id=%s" class="todo-detail-link">详情</a>' % tid, body)

    def _find_task_row(self, body):
        idx = body.find('class="list-item todo-task-row"')
        if idx < 0:
            return None
        return body[idx:idx + 900]

    def test_todo_list_row_layout(self):
        # 三行布局：第一行内容、第二行标签、第三行操作
        self.json_request_return_dict("/api/v1/todo/create", method="POST",
                                      data=dict(content="三行布局待办", project_id="1"))
        body = self.request_app("/todo/task?project_id=1").data.decode("utf-8")
        row = self._find_task_row(body)
        self.assertIsNotNone(row)
        pos_content = row.find('class="todo-task-content"')
        pos_tag = row.find('class="tag ')
        pos_actions = row.find("todo-task-actions")
        self.assertTrue(0 <= pos_content < pos_tag < pos_actions,
                        "期望顺序为 内容 -> 标签 -> 操作, got %s/%s/%s" % (
                            pos_content, pos_tag, pos_actions))

    def test_todo_list_row_shows_create_date(self):
        # 列表行展示创建日期（YYYY-MM-DD）
        self.json_request_return_dict("/api/v1/todo/create", method="POST",
                                      data=dict(content="创建日期待办", project_id="1"))
        lst = self.json_request_return_dict("/api/v1/todo/list?project_id=1")
        task = [item for item in lst["data"]["items"]
                if item["content"] == "创建日期待办"][0]
        from xnote_handlers.todo.todo_model import format_date_ms
        create_date = format_date_ms(task["create_time"])
        self.assertTrue(create_date)  # 前置：create_time 有效

        body = self.request_app("/todo/task?project_id=1").data.decode("utf-8")
        row = self._find_task_row(body)
        self.assertIsNotNone(row)
        self.assertIn("创建 %s" % create_date, row)

    def test_archive_action_link_in_project(self):
        # 项目行的【归档】操作链接(action=archive)，且不再有删除(action=delete)
        self.json_request_return_dict("/api/v1/project/create", method="POST",
                                      data=dict(name="归档动作项目"))
        project_page = self.request_app("/todo").data.decode("utf-8")
        self.assertRegex(project_page, r'data-url="[^"]*action=archive')
        self.assertNotIn("action=delete", project_page)

    def test_task_row_has_no_delete_button(self):
        # 待办行已移除【删除】按钮（保留取消），页面不存在删除入口
        self.json_request_return_dict("/api/v1/todo/create", method="POST",
                                      data=dict(content="无删除待办", project_id="1"))
        task_page = self.request_app("/todo/task?project_id=1").data.decode("utf-8")
        self.assertNotIn("action=delete", task_page)
        self.assertIn("action=cancel", task_page)

    def test_search_box_present(self):
        # 待办行已移除【删除】按钮（保留取消），页面不存在删除入口
        self.json_request_return_dict("/api/v1/todo/create", method="POST",
                                      data=dict(content="无删除待办", project_id="1"))
        task_page = self.request_app("/todo/task?project_id=1").data.decode("utf-8")
        self.assertNotIn("action=delete", task_page)
        self.assertIn("action=cancel", task_page)

    def test_global_search_configured(self):
        # 待办页面复用顶部全局搜索组件：搜索表单指向 /todo/task
        self.json_request_return_dict("/api/v1/todo/create", method="POST",
                                      data=dict(content="全局搜索待办", project_id="1"))
        task_page = self.request_app("/todo/task?project_id=1").data.decode("utf-8")
        self.assertIn("nav-search-input", task_page)   # 顶部全局搜索输入框
        self.assertIn('action="/todo/task"', task_page)  # 提交到待办搜索
        # 项目首页(跨项目)同样指向 /todo/task
        home = self.request_app("/todo").data.decode("utf-8")
        self.assertIn('action="/todo/task"', home)

    def test_global_search_default_includes_todo(self):
        # 全局【默认】综合搜索也应检索到新待办模块的内容（折叠为 tools 桶里的单条摘要，参考随手记）
        tid = self.json_request_return_dict(
            "/api/v1/todo/create", method="POST",
            data=dict(content="综合搜索命中待办T", project_id="1"))["data"]

        # 直接校验 search_todo 处理器：折叠为单条摘要，不逐条展开待办详情
        from xnote_handlers.todo.todo_search import search_todo
        from xnote.core.models import SearchContext
        import xauth
        ctx = SearchContext(key="综合搜索命中待办T")
        ctx.user_id = xauth.current_user_id()
        search_todo(ctx)
        summaries = [f for f in ctx.tools
                     if getattr(f, "name", "").startswith("搜索到") and "个待办" in f.name]
        self.assertEqual(len(summaries), 1)
        self.assertIn("/todo/task?model=task", summaries[0].url)
        self.assertIn("status=all", summaries[0].url)
        self.assertNotIn("/todo/detail?task_id=%s" % tid, [getattr(f, "url", "") for f in ctx.tools])

        # 分类搜索走 do_search_by_type，不触发 search 事件，不混入新待办(避免和旧 task 标签冲突)
        note_body = self.request_app("/search?search_type=note&key=综合搜索命中待办T").data.decode("utf-8")
        self.assertNotIn("/todo/task?model=task", note_body)

    def test_global_search_filters_results(self):
        # 模拟全局搜索组件提交：跨项目搜索 model=task&key=...
        self.json_request_return_dict("/api/v1/todo/create", method="POST",
                                      data=dict(content="searchable todo", project_id="1"))
        self.json_request_return_dict("/api/v1/todo/create", method="POST",
                                      data=dict(content="irrelevant todo", project_id="1"))
        body = self.request_app("/todo/task?model=task&key=searchable").data.decode("utf-8")
        self.assertIn("searchable", body)
        self.assertNotIn("irrelevant", body)

        # 当前项目内搜索（header search_ext_dict 带 project_id + status=all）
        body2 = self.request_app(
            "/todo/task?project_id=1&status=all&key=searchable").data.decode("utf-8")
        self.assertIn("searchable", body2)
        self.assertNotIn("irrelevant", body2)

        # 已完成(非待办)的待办也能被命中（status=all 不过滤状态）
        done_id = self.json_request_return_dict(
            "/api/v1/todo/create", method="POST",
            data=dict(content="finished search todo", project_id="1"))["data"]
        self.json_request_return_dict(
            "/api/v1/todo/status", method="POST",
            data=dict(task_id=done_id, action="finish"))
        done_body = self.request_app(
            "/todo/task?project_id=1&status=all&key=finished").data.decode("utf-8")
        self.assertIn("finished", done_body)

    def test_todo_not_started_tag_is_orange(self):
        # 【未开始】状态标签使用 orange
        self.json_request_return_dict("/api/v1/todo/create", method="POST",
                                      data=dict(content="橙色标签待办", project_id="1"))
        body = self.request_app("/todo/task?project_id=1").data.decode("utf-8")
        self.assertIn('<span class="tag orange">未开始</span>', body)

    def test_todo_list_comment_action(self):
        # 列表行操作区提供【评论】，弹窗地址指向评论页面
        tid = self.json_request_return_dict("/api/v1/todo/create", method="POST",
                                           data=dict(content="评论入口待办", project_id="1"))["data"]
        body = self.request_app("/todo/task?project_id=1").data.decode("utf-8")
        self.assertIn("xnote.todo.openCommentDialog(this)", body)
        self.assertIn('data-url="/comment/dialog?task_id=%s"' % tid, body)

    def test_todo_comment_dialog_page(self):
        tid = self.json_request_return_dict("/api/v1/todo/create", method="POST",
                                           data=dict(content="弹窗评论待办", project_id="1"))["data"]
        resp = self.request_app("/comment/dialog?task_id=%s" % tid)
        self.assertEqual("200 OK", resp.status)
        body = resp.data.decode("utf-8")
        self.assertIn("commentText", body)            # 评论输入框
        self.assertIn('id="comments"', body)          # 评论列表服务端直接渲染（无需前端 AJAX）
        self.assertIn("/comment/save", body)

    def test_todo_list_default_filter(self):
        # 默认【待办】Tab，且包含 待办/全部/未开始/进行中/完成/取消
        self.json_request_return_dict("/api/v1/todo/create", method="POST",
                                      data=dict(content="默认筛选待办", project_id="1"))
        body = self.request_app("/todo/task?project_id=1").data.decode("utf-8")
        self.assertIn('data-tab-default="pending"', body)
        self.assertIn('data-tab-value="pending"', body)
        self.assertIn('data-tab-value="all"', body)
        self.assertIn('data-tab-value="not_started"', body)
        self.assertIn('data-tab-value="in_progress"', body)
        self.assertIn('data-tab-value="done"', body)
        self.assertIn('data-tab-value="canceled"', body)

    def test_project_pending_done_counts(self):
        pid = self.json_request_return_dict("/api/v1/project/create", method="POST",
                                            data=dict(name="计数页面项目"))["data"]
        self.json_request_return_dict("/api/v1/todo/create", method="POST",
                                      data=dict(content="计数待办", project_id=str(pid)))
        body = self.request_app("/todo").data.decode("utf-8")
        # 通过本项目的 project_id 定位行（测试库中存在多个同名/种子项目，
        # 直接用 body.find(名称) 会命中错误的行）
        marker = "model=project&amp;project_id=%d" % pid
        idx = body.find(marker)
        self.assertGreater(idx, 0)
        row = self._find_project_row(body, pid)
        self.assertIsNotNone(row)
        self.assertIn("待办 1", row)
        self.assertIn("完成 0", row)

    def _find_project_row(self, body, project_id):
        """截取一个项目列表行的 HTML（从外层 <a> 开始）"""
        marker = 'class="list-item-link todo-project-row" href="/todo/task?project_id=%s"' % project_id
        idx = body.find(marker)
        if idx < 0:
            return None
        start = body.rfind("<", 0, idx)
        return body[start:start + 1200]

    def test_project_row_links_to_project_tasks(self):
        # 项目行链接指向该项目自己的待办列表（project_id 正确），而非其它项目/固定地址
        pid = self.json_request_return_dict("/api/v1/project/create", method="POST",
                                            data=dict(name="链接项目"))["data"]
        body = self.request_app("/todo").data.decode("utf-8")
        row = self._find_project_row(body, pid)
        self.assertIsNotNone(row, "未找到 project_id=%s 的项目行" % pid)
        self.assertIn("链接项目", row)

    def test_project_row_has_edit_and_archive_actions(self):
        # 项目行提供编辑/归档入口，且归档地址指向本项目（不是删除）
        pid = self.json_request_return_dict("/api/v1/project/create", method="POST",
                                            data=dict(name="操作项目"))["data"]
        body = self.request_app("/todo").data.decode("utf-8")
        row = self._find_project_row(body, pid)
        self.assertIsNotNone(row, "未找到 project_id=%s 的项目行" % pid)
        self.assertIn("action=edit&amp;model=project&amp;project_id=%s" % pid, row)
        self.assertIn("action=archive&amp;model=project&amp;project_id=%s" % pid, row)
        self.assertNotIn("action=delete", row)

    def test_todo_pagination(self):
        pid = self.json_request_return_dict("/api/v1/project/create", method="POST",
                                            data=dict(name="分页测试项目"))["data"]
        for i in range(51):
            self.json_request_return_dict("/api/v1/todo/create", method="POST",
                                          data=dict(content="分页%02d" % i, project_id=str(pid)))
        p1 = self.request_app("/todo/task?project_id=%s" % pid).data.decode("utf-8")
        self.assertIn("pagenation", p1)
        self.assertEqual(p1.count('class="list-item todo-task-row"'), 50)
        self.assertIn("page=2", p1)

        p2 = self.request_app("/todo/task?project_id=%s&page=2" % pid).data.decode("utf-8")
        self.assertEqual(p2.count('class="list-item todo-task-row"'), 1)

    def test_todo_edit_form(self):
        # 新建待办的编辑表单（ajax 局部渲染）
        resp = self.request_app("/todo/task?action=edit&model=task&project_id=1")
        self.assertEqual("200 OK", resp.status)
        body = resp.data.decode("utf-8")
        self.assertIn('name="content"', body)
        self.assertIn("<textarea", body)  # 内容使用 textarea
        # textarea 高度按内容自动调整（初始化钩子限定在具体的 form 内）
        self.assertRegex(body, r'initAutoResizeTextarea\("#xnoteForm\w+ textarea"\)')
        # 所属项目可选（不提供【未分类】）
        self.assertIn('name="project_id"', body)
        self.assertIn("<select", body)
        self.assertNotIn('<option value="0">', body)
        self.assertNotIn("未分类", body)
        # 状态可选
        self.assertIn('name="status"', body)
        self.assertIn("未开始", body)
        self.assertIn("进行中", body)
        # 完成时间/创建时间/更新时间只读展示
        self.assertIn("完成时间", body)
        self.assertRegex(body, r'name="done_time"[^>]*readonly')
        self.assertIn("创建时间", body)
        self.assertRegex(body, r'name="create_time"[^>]*readonly')
        self.assertIn("更新时间", body)
        self.assertRegex(body, r'name="update_time"[^>]*readonly')


class TestTodoForm(BaseTestCase):
    """页面插件表单流程测试(创建/状态变更/移动/删除)"""

    def _post_form(self, url, **fields):
        return self.json_request_return_dict(url, method="POST",
                                             data=dict(data=json.dumps(fields)))

    def test_create_task_via_form(self):
        resp = self._post_form("/todo/task?action=save&model=task",
                               project_id="1", content="表单待办",
                               priority="high", begin_time="", end_time="")
        self.assertTrue(resp["success"])

        lst = self.json_request_return_dict("/api/v1/todo/list?project_id=1")
        contents = [item["content"] for item in lst["data"]["items"]]
        self.assertIn("表单待办", contents)

    def test_save_task_status_via_form(self):
        # 通过编辑表单改状态：完成时间同步维护
        self._post_form("/todo/task?action=save&model=task",
                        project_id="1", content="表单状态待办", priority="normal",
                        status="done", begin_time="", end_time="")
        lst = self.json_request_return_dict("/api/v1/todo/list?project_id=1")
        task = [item for item in lst["data"]["items"]
                if item["content"] == "表单状态待办"][0]
        self.assertEqual(task["status"], "done")
        self.assertTrue(task["done_time"] > 0)

        # 改回【未开始】会清空完成时间
        self._post_form("/todo/task?action=save&model=task", task_id=str(task["task_id"]),
                        project_id="1", content="表单状态待办", priority="normal",
                        status="not_started", begin_time="", end_time="")
        lst2 = self.json_request_return_dict("/api/v1/todo/list?project_id=1")
        found = [item for item in lst2["data"]["items"]
                 if item["task_id"] == task["task_id"]][0]
        self.assertEqual(found["status"], "not_started")
        self.assertEqual(found["done_time"], 0)

    def test_save_task_requires_project(self):
        # 保存待办必须有归属的项目
        resp = self._post_form("/todo/task?action=save&model=task", project_id="0",
                               content="缺少项目待办", priority="normal",
                               status="not_started", begin_time="", end_time="")
        self.assertFalse(resp["success"])

        lst = self.json_request_return_dict("/api/v1/todo/list?project_id=0")
        contents = [item["content"] for item in lst["data"]["items"]]
        self.assertNotIn("缺少项目待办", contents)

    def test_create_project_via_form(self):
        resp = self._post_form("/todo?action=save&model=project",
                               name="表单项目", desc="来自表单")
        self.assertTrue(resp["success"])

        lst = self.json_request_return_dict("/api/v1/project/list")
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
                        self.json_request_return_dict("/api/v1/project/list")["data"]]
        self.assertNotIn("归档项目", active_names)
        archived_names = [item["name"] for item in
                          self.json_request_return_dict("/api/v1/project/list?status=archived")["data"]]
        self.assertIn("归档项目", archived_names)

    def test_status_and_delete_via_form(self):
        self._post_form("/todo/task?action=save&model=task",
                        project_id="1", content="待完成", priority="normal",
                        begin_time="", end_time="")
        lst = self.json_request_return_dict("/api/v1/todo/list?project_id=1")
        task = [item for item in lst["data"]["items"] if item["content"] == "待完成"][0]
        task_id = task["task_id"]

        # 完成
        resp = self.json_request_return_dict(
            "/todo/task?action=finish&model=task&project_id=1&task_id=%s" % task_id)
        self.assertTrue(resp["success"])
        lst2 = self.json_request_return_dict("/api/v1/todo/list?project_id=1")
        found = [item for item in lst2["data"]["items"] if item["task_id"] == task_id][0]
        self.assertEqual(found["status"], "done")

        # 删除（保留 REST 接口 /api/v1/todo/delete）
        resp = self.json_request_return_dict(
            "/api/v1/todo/delete", method="POST", data=dict(task_id=task_id))
        self.assertTrue(resp["success"])

    def test_reopen_canceled_task(self):
        self._post_form("/todo/task?action=save&model=task",
                        project_id="1", content="取消后重开", priority="normal",
                        begin_time="", end_time="")
        lst = self.json_request_return_dict("/api/v1/todo/list?project_id=1")
        task_id = [item for item in lst["data"]["items"]
                   if item["content"] == "取消后重开"][0]["task_id"]

        # 取消
        resp = self.json_request_return_dict(
            "/todo/task?action=cancel&model=task&project_id=1&task_id=%s" % task_id)
        self.assertTrue(resp["success"])

        # 已取消的任务在【全部】视图仍提供【重开】入口，且状态变更不需要确认
        page = self.request_app("/todo/task?project_id=1&status=all").data.decode("utf-8")
        self.assertIn(
            "action=reset&amp;model=task&amp;project_id=1&amp;task_id=%s" % task_id, page)
        self.assertIn("xnote.table.handleAjaxAction(this)", page)
        # 待办行已移除删除按钮，不再有需确认的删除操作
        self.assertNotIn("action=delete", page)

        # 重开生效（回到未开始）
        resp = self.json_request_return_dict(
            "/todo/task?action=reset&model=task&project_id=1&task_id=%s" % task_id)
        self.assertTrue(resp["success"])
        lst2 = self.json_request_return_dict("/api/v1/todo/list?project_id=1")
        found = [item for item in lst2["data"]["items"] if item["task_id"] == task_id][0]
        self.assertEqual(found["status"], "not_started")

    def test_move_task_project_via_form(self):
        # 建源/目标两个项目
        pid1 = self.json_request_return_dict(
            "/api/v1/project/create", method="POST", data=dict(name="移动源"))["data"]
        pid2 = self.json_request_return_dict(
            "/api/v1/project/create", method="POST", data=dict(name="移动目标"))["data"]

        # 在 pid1 下建待办
        self._post_form("/todo/task?action=save&model=task",
                        project_id=str(pid1), content="移动待办",
                        priority="normal", begin_time="", end_time="")
        lst = self.json_request_return_dict("/api/v1/todo/list?project_id=%s" % pid1)
        task_id = [item for item in lst["data"]["items"]
                   if item["content"] == "移动待办"][0]["task_id"]

        # 通过编辑表单改到 pid2
        resp = self._post_form("/todo/task?action=save&model=task",
                               task_id=str(task_id), project_id=str(pid2),
                               content="移动待办", priority="normal",
                               begin_time="", end_time="")
        self.assertTrue(resp["success"])

        # pid2 下能查到，pid1 下查不到
        ids2 = [item["task_id"] for item in
                self.json_request_return_dict("/api/v1/todo/list?project_id=%s" % pid2)["data"]["items"]]
        self.assertIn(task_id, ids2)
        ids1 = [item["task_id"] for item in
                self.json_request_return_dict("/api/v1/todo/list?project_id=%s" % pid1)["data"]["items"]]
        self.assertNotIn(task_id, ids1)

    def _create_task(self, content, project_id="1"):
        self._post_form("/todo/task?action=save&model=task", project_id=str(project_id),
                        content=content, priority="normal", begin_time="2026-09-12", end_time="")
        lst = self.json_request_return_dict("/api/v1/todo/list?project_id=%s" % project_id)
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
        # 详情页内嵌评论列表（复用 note 评论组件，服务端直接渲染）
        self.assertIn("commentText", body)
        self.assertIn('id="comments"', body)
        self.assertIn("todo_task", body)

    def test_todo_comment_flow(self):
        task_id = self._create_task("评论待办")
        target_id = to_comment_target_id(task_id)

        # 发表评论
        resp = self.json_request_return_dict(
            "/comment/save", method="POST",
            data=dict(note_id=str(target_id), content="待办评论内容", type="todo_task"))
        self.assertTrue(resp["success"])

        # 列表能查到
        html = self.request_app(
            "/comment/list?note_id=%s&type=todo_task&resp_type=html" % target_id).data.decode("utf-8")
        self.assertIn("待办评论内容", html)

        # 隔离：同数字 id 的笔记视角查不到该评论（target_id 独立空间）
        note_comments, _ = dao_comment.list_parent_comments(task_id, type="")
        self.assertFalse(any(c.content == "待办评论内容" for c in note_comments))


if __name__ == "__main__":
    unittest.main()
