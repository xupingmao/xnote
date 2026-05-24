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
        # clean comments
        data = json_request_return_list(f"/note/comments?note_id={note_id}")
        for comment in data:
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
