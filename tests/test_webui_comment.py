# -*- coding:utf-8 -*-
"""CommentBox 组件渲染测试（评论列表改为前端通过独立接口异步加载）

验证点:
1. CommentBox 只在静态页面输出 #comment-box 容器与加载接口所需的 data-* 配置,
   评论内容不再静态输出(改由前端调用独立接口拉取)。
2. 独立的列表加载接口(/comment/list, resp_type=html)
   返回评论列表 HTML 片段(含评论内容与对应删除地址)。
"""
from .test_base import BaseTestCase, init as init_app
from tests.test_base_note import delete_note_for_test, create_note_for_test
from xnote_handlers.comment.dao_comment import list_comments
from xnote.webui.comment import CommentBox

app = init_app()


def _delete_comments(note_id):
    for comment in list_comments(note_id, offset=0, limit=1000):
        from tests.test_comment import delete_comment_for_test
        delete_comment_for_test(comment.id)


class TestCommentBox(BaseTestCase):

    def test_render_note_comment(self):
        """笔记评论组件渲染容器 + 加载接口配置; 内容由 /comment/list 异步返回"""
        delete_note_for_test(name="comment-box-test")
        note_id = create_note_for_test(type="md", name="comment-box-test")
        _delete_comments(note_id)

        from tests.test_comment import create_comment_for_test
        create_comment_for_test(note_id=note_id, user_id=1, content="comment-box-content")
        try:
            box = CommentBox(target_id=note_id, list_type="note_id", show_edit=True)
            html = box.render()

            self.assertIn('id="comment-box"', html)
            self.assertIn('id="comments"', html)
            # 加载接口配置
            self.assertIn('data-list-url="/comment/list"', html)
            self.assertIn('data-target-id="%s"' % note_id, html)
            self.assertIn('data-show-edit="true"', html)
            # 内容不再静态输出
            self.assertNotIn("comment-box-content", html)

            # 独立的列表加载接口返回 HTML 片段（含评论内容与删除地址）
            body = self.request_app(
                "/comment/list?note_id=%s&list_type=note_id&resp_type=html&show_edit=true" % note_id
            ).data.decode("utf-8")
            self.assertIn("comment-box-content", body)
            self.assertIn("/comment/delete", body)
        finally:
            _delete_comments(note_id)
            delete_note_for_test(name="comment-box-test")

    def test_comment_page_param(self):
        """评论分页参数使用 comment_page(而非 page), 避免与页面自身分页冲突;
        分页链接也应以 comment_page 呈现"""
        from xnote.core import xconfig
        from tests.test_comment import create_comment_for_test

        delete_note_for_test(name="comment-page-test")
        note_id = create_note_for_test(type="md", name="comment-page-test")
        _delete_comments(note_id)

        # 造出多于一页的评论(PAGE_SIZE + 1)
        page_size = xconfig.PAGE_SIZE
        for i in range(page_size + 1):
            create_comment_for_test(note_id=note_id, user_id=1, content="page-content-%s" % i)
        try:
            # 组件渲染 data-comment-page 默认为 1
            box = CommentBox(target_id=note_id, list_type="note_id", show_edit=True)
            html = box.render()
            self.assertIn('data-comment-page="1"', html)
            self.assertNotIn('data-page="', html)

            # 第 2 页应返回分页链接, 且链接指向 comment_page=2
            body = self.request_app(
                "/comment/list?note_id=%s&list_type=note_id&resp_type=html&comment_page=2" % note_id
            ).data.decode("utf-8")
            self.assertIn("comment_page=2", body)

            # 显式传入 comment_page 时, 组件按传入值渲染
            box2 = CommentBox(target_id=note_id, list_type="note_id", show_edit=True, comment_page=3)
            self.assertIn('data-comment-page="3"', box2.render())
        finally:
            _delete_comments(note_id)
            delete_note_for_test(name="comment-page-test")

    def test_render_todo_branch_delete_url(self):
        """todo 评论 target_id 落入独立区间时, 列表接口应使用统一的删除地址"""
        from xnote_handlers.comment import COMMENT_TARGET_OFFSET, to_comment_target_id
        from xnote_handlers.todo.dao import TodoDao
        from xnote_handlers.todo.todo_model import TodoRecord, TodoStatusEnum, TodoPriorityEnum
        from xnote_handlers.comment.dao_comment import CommentDao, CommentVO, delete_comment

        # 待办评论接口会校验待办归属, 这里先创建一个真实的待办
        todo = TodoRecord()
        todo.user = "admin"
        todo.user_id = 1
        todo.content = "todo-for-comment"
        todo.status = TodoStatusEnum.not_started.value
        todo.priority = TodoPriorityEnum.normal.value
        task_id = TodoDao.create(todo)
        self.assertTrue(task_id > 0)

        todo_target_id = to_comment_target_id(task_id)
        comment = CommentVO()
        comment.user_id = 1
        comment.note_id = todo_target_id
        comment.type = "todo_task"
        comment.content = "todo-box-content"
        CommentDao.create(comment=comment)
        try:
            box = CommentBox(target_id=todo_target_id, list_type="note_id",
                             show_edit=True, create_type="todo_task", list_url="/comment/list")
            html = box.render()
            self.assertIn('id="comment-box"', html)
            self.assertIn('id="comments"', html)
            self.assertIn('data-list-url="/comment/list"', html)
            self.assertIn('data-target-id="%s"' % todo_target_id, html)
            self.assertIn('data-create-type="todo_task"', html)
            self.assertNotIn("todo-box-content", html)

            body = self.request_app(
                "/comment/list?note_id=%s&list_type=note_id&type=todo_task&resp_type=html&show_edit=true" % todo_target_id
            ).data.decode("utf-8")
            self.assertIn("todo-box-content", body)
            self.assertIn("/comment/delete", body)
        finally:
            delete_comment(comment.id)
            TodoDao.delete(task_id)
