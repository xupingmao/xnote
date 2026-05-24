# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-01 12:52:24
@LastEditors  : xupingmao
@LastEditTime : 2022-05-01 15:09:21
@FilePath     : /xnote/tests/test_dict.py
"""

import copy

from .test_base import json_request, json_request_return_dict, BaseTestCase
from .test_base import init as init_app
from xnote_handlers.dict import dict_dao
from xnote_handlers.note.dao import NoteIndexDao, NoteIndexDO
from xnote_handlers.note.dao_comment import CommentDao, CommentVO
from xnote.core.models import SearchContext
from xnote.core import xauth
from tests.test_base_note import delete_note_for_test, create_note_for_test
from tests.test_base import json_request_return_list
from tests.test_base import login_test_user, logout_test_user


app = init_app()

def delete_comment_for_test(id):
    json_request("/note/comment/delete", method = "POST", data = dict(comment_id = id))

def create_comment_for_test(note_id=0, user_id=0, content="hello"):
    assert note_id > 0
    comment = CommentVO()
    comment.user_id = user_id
    comment.note_id = note_id
    comment.content = content
    return CommentDao.create(comment=comment)

class TestMain(BaseTestCase):

    def test_note_comment(self):
        delete_note_for_test(name="comment-test")
        note_id = create_note_for_test(type="md", name="comment-test")
        
        # 清理该笔记下的评论
        data = json_request_return_list(f"/note/comments?note_id={note_id}")
        for comment in data:
            delete_comment_for_test(comment['id'])
        
        # 清理用户 admin 的所有评论（避免用户维度列表受影响）
        user_comments = json_request_return_list("/note/comment/list?list_type=user")
        for comment in user_comments:
            if comment.get("user_id") == 1:  # admin 的 user_id
                delete_comment_for_test(comment['id'])

        # 创建一个评论
        request = dict(note_id = str(note_id), content = "hello")
        json_request("/note/comment/save", method="POST", data = request)

        # 查询评论
        data = json_request_return_list(f"/note/comments?note_id={note_id}")
        self.assertEqual(1, len(data))
        self.assertEqual("hello", data[0]['content'])

        comment_id = data[0]["id"]

        # 获取编辑对话框
        self.check_OK("/note/comment?comment_id=%s&p=edit" % comment_id)

        # 更新评论
        data = json_request_return_dict("/note/comment?comment_id=%s&p=update&content=%s" % (comment_id, "#TOPIC# hello"))
        self.assertEqual("success", data["code"])

        # 置顶
        resp = json_request_return_dict(f"/note/comment/update_pin_level", method="POST", data=dict(comment_id=comment_id, pin_level=1))
        assert resp["success"] == True
        index = CommentDao.get_index_by_id(comment_id=comment_id)
        assert index is not None
        assert index.pin_level == 1

        # 取消置顶
        resp = json_request_return_dict(f"/note/comment/update_pin_level", method="POST", data=dict(comment_id=comment_id, pin_level=0))
        assert resp["success"] == True
        index = CommentDao.get_index_by_id(comment_id=comment_id)
        assert index is not None
        assert index.pin_level == 0

        # 置顶其他用户的评论
        test_user_id = xauth.UserDao.get_id_by_name("test")
        other_comment_id = create_comment_for_test(note_id=note_id, user_id=test_user_id, content="this is comment from user test")
        resp = json_request_return_dict(f"/note/comment/update_pin_level", method="POST", data=dict(comment_id=other_comment_id, pin_level=1))
        assert resp["success"] == True

        # 置顶其他笔记评论报错 TODO
        # other_note_id = create_note_for_test()
        # other_comment_id = create_comment_for_test(note_id=other_note_id, user_id=test_user_id, content="this is comment from user test")
        # resp = json_request_return_dict(f"/note/comment/update_pin_level", method="POST", data=dict(comment_id=comment_id, pin_level=1))
        # assert resp["success"] == False

        # 查询用户维度评论列表
        data = json_request_return_list("/note/comment/list?list_type=user")
        self.assertEqual(1, len(data))

        # 我的所有评论
        self.check_OK("/note/comment/mine")

        # 搜索评论
        from xnote_handlers.note.comment import search_comment_detail, search_comment_summary
        ctx = SearchContext(key = "hell")
        ctx.user_name = xauth.current_name_str()
        ctx.words = ["hello"]
        summary_ctx = copy.deepcopy(ctx)

        search_comment_detail(ctx)
        self.assertEqual(1, len(ctx.messages))

        search_comment_summary(summary_ctx)
        
        print("搜索评论汇总结果:", summary_ctx)

        self.assertEqual(1, len(summary_ctx.messages))


        # 删除评论
        result = json_request_return_dict("/note/comment/delete", method = "POST", 
            data = dict(comment_id = comment_id))
        self.assertEqual("success", result["code"])

        data = json_request_return_list("/note/comment/list?list_type=user")
        self.assertEqual(0, len(data))


    def test_note_comment_not_login(self):
        delete_note_for_test(name="comment-test")
        note_id = create_note_for_test(type="md", name="comment-test")
        note_index = NoteIndexDao.get_by_id(note_id)
        assert note_index != None

        try:
            logout_test_user()
            self.check_303(f"/note/comments?note_id={note_id}")
            # 改成public
            note_index.is_public = True
            NoteIndexDO.update(note_index)
            self.check_OK(f"/note/comments?note_id={note_id}")
        finally:
            login_test_user()

    def test_comment_create_time_update_time(self):
        """测试评论的 create_time/update_time 字段（毫秒时间戳）"""
        delete_note_for_test(name="comment-time-test")
        note_id = create_note_for_test(type="md", name="comment-time-test")
        
        # 清理评论
        data = json_request_return_list(f"/note/comments?note_id={note_id}")
        for comment in data:
            delete_comment_for_test(comment['id'])
        
        # 创建评论
        request = dict(note_id=str(note_id), content="test time fields")
        json_request("/note/comment/save", method="POST", data=request)
        
        # 查询评论，验证 create_time/update_time 字段
        data = json_request_return_list(f"/note/comments?note_id={note_id}")
        self.assertEqual(1, len(data))
        
        comment = data[0]
        self.assertIn("create_time", comment)
        self.assertIn("update_time", comment)
        
        # 验证时间戳是毫秒级别的（大于10^12）
        create_time = comment["create_time"]
        update_time = comment["update_time"]
        self.assertGreater(create_time, 10**12, "create_time 应该是毫秒时间戳")
        self.assertGreater(update_time, 10**12, "update_time 应该是毫秒时间戳")
        self.assertEqual(create_time, update_time, "新建评论的 create_time 和 update_time 应该相等")
        
        # 获取评论详情，验证 date 属性
        comment_id = comment["id"]
        from xnote_handlers.note.dao_comment import get_comment
        comment_record = get_comment(comment_id)
        self.assertIsNotNone(comment_record)
        self.assertEqual(comment_record.create_time, create_time)
        self.assertEqual(comment_record.update_time, update_time)
        self.assertNotEqual(comment_record.date, "", "date 属性应该有值")
        self.assertEqual(len(comment_record.date), 10, "date 格式应该是 YYYY-MM-DD")
        
        # 更新评论，验证 update_time 变化
        import time
        time.sleep(0.01)  # 等待10毫秒确保时间戳有差异
        data = json_request_return_dict(f"/note/comment?comment_id={comment_id}&p=update&content=updated content")
        self.assertEqual("success", data["code"])
        
        # 再次获取评论，验证 update_time 已更新
        updated_record = get_comment(comment_id)
        self.assertGreater(updated_record.update_time, update_time, "更新后 update_time 应该增大")
        
        # 清理
        delete_comment_for_test(comment_id)

    def test_comment_replies(self):
        """测试评论回复功能"""
        # 获取当前用户
        user_id = xauth.current_user_id()
        
        # 先尝试获取已有的笔记，优先用 test_note_comment 用的 comment-test
        note_index = NoteIndexDao.get_by_name(creator_id=user_id, name="comment-test")
        if note_index is not None:
            note_id = note_index.id
        else:
            # 如果找不到，用任意一个已有的笔记
            from xnote_handlers.note.dao_base import list_by_parent
            notes = list_by_parent(creator_id=user_id, parent_id=0, offset=0, limit=10)
            if len(notes) > 0:
                note_id = notes[0].id
            else:
                # 如果没有，就创建一个
                note_id = 1  # default_group_id 这个已经存在了
        
        # 清理该笔记下的评论
        data = json_request_return_list(f"/note/comments?note_id={note_id}")
        for comment in data:
            delete_comment_for_test(comment['id'])
        
        # 清理用户 admin 的所有评论（避免用户维度列表受影响）
        user_comments = json_request_return_list("/note/comment/list?list_type=user")
        for comment in user_comments:
            if comment.get("user_id") == 1:  # admin 的 user_id
                delete_comment_for_test(comment['id'])
        
        # 创建主评论
        request = dict(note_id=str(note_id), content="main comment")
        json_request("/note/comment/save", method="POST", data=request)
        
        # 查询主评论
        data = json_request_return_list(f"/note/comments?note_id={note_id}")
        self.assertEqual(1, len(data))
        main_comment_id = data[0]["id"]
        main_user_id = data[0]["user_id"]
        main_user_name = data[0]["user"]
        
        # 验证回复数量为0
        self.assertEqual(0, data[0]["reply_count"])
        
        # 创建第一个回复 - 回复主评论
        reply1_request = dict(
            note_id=str(note_id),
            content="first reply to main comment",
            parent_comment_id=str(main_comment_id),
            ref_comment_id=str(main_comment_id),
            ref_user_id=str(main_user_id)
        )
        json_request("/note/comment/save", method="POST", data=reply1_request)
        
        # 验证回复数量变为1
        data = json_request_return_list(f"/note/comments?note_id={note_id}")
        self.assertEqual(1, len(data))
        self.assertEqual(1, data[0]["reply_count"])
        
        # 获取回复列表 - 测试JSON接口
        reply_data = json_request_return_dict(
            f"/note/comment/replies?note_id={note_id}&parent_comment_id={main_comment_id}"
        )
        self.assertTrue(reply_data["success"])
        replies = reply_data["data"]["replies"]
        self.assertEqual(1, len(replies))
        self.assertEqual("first reply to main comment", replies[0]["content"])
        self.assertEqual(main_comment_id, replies[0]["parent_comment_id"])
        self.assertEqual(main_comment_id, replies[0]["ref_comment_id"])
        self.assertEqual(main_user_id, replies[0]["ref_user_id"])
        
        # 获取回复列表 - 测试HTML接口
        from tests.test_base import request_html
        html_resp = request_html(
            f"/note/comment/reply_list?note_id={note_id}&parent_comment_id={main_comment_id}"
        )
        html_str = html_resp.decode("utf-8")
        self.assertIn("first", html_str)
        self.assertIn("reply", html_str)
        
        # 创建第二个回复 - 回复第一个回复
        reply1_id = replies[0]["id"]
        reply1_user_id = replies[0]["user_id"]
        reply2_request = dict(
            note_id=str(note_id),
            content="reply to first reply",
            parent_comment_id=str(main_comment_id),
            ref_comment_id=str(reply1_id),
            ref_user_id=str(reply1_user_id)
        )
        json_request("/note/comment/save", method="POST", data=reply2_request)
        
        # 验证回复数量变为2
        data = json_request_return_list(f"/note/comments?note_id={note_id}")
        self.assertEqual(2, data[0]["reply_count"])
        
        # 获取回复列表，验证第二条回复
        reply_data = json_request_return_dict(
            f"/note/comment/replies?note_id={note_id}&parent_comment_id={main_comment_id}"
        )
        replies = reply_data["data"]["replies"]
        self.assertEqual(2, len(replies))
        self.assertEqual("reply to first reply", replies[1]["content"])
        self.assertEqual(reply1_id, replies[1]["ref_comment_id"])
        self.assertEqual(reply1_user_id, replies[1]["ref_user_id"])
        
        # 直接查询评论验证 ref_user 字段是否被正确处理
        from xnote_handlers.note.comment import process_comments
        from xnote_handlers.note.dao_comment import list_replies
        reply_comments, _ = list_replies(note_id, main_comment_id, 0, 10)
        process_comments(reply_comments, show_note=False)
        
        # 验证第二个回复的 ref_user 是否正确填充
        reply2_comment = reply_comments[1]
        reply1_user = reply_comments[0]["user"]
        self.assertEqual(reply1_user, reply2_comment.ref_user)
        
        # 清理评论
        data = json_request_return_list(f"/note/comments?note_id={note_id}")
        for comment in data:
            delete_comment_for_test(comment['id'])
