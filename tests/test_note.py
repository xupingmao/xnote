# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/10/05 20:23:43
# @modified 2022/08/08 22:44:29
# @filename test_note.py

import logging
import time
import copy
import pdb
import xutils
# cannot perform relative import
try:
    import test_base
    from test_base import login_test_user, logout_test_user
except ImportError:
    from tests import test_base
    from tests.test_base import login_test_user, logout_test_user

from xnote.core import xauth

from handlers.note.dao import get_by_id, get_by_name, visit_note, get_by_user_skey
from handlers.note import dao_comment
from handlers.note import dao_delete, dao_tag
from handlers.note import html_importer
from handlers.note import dao as note_dao

from xutils import Storage
from xutils import textutil

app          = test_base.init()
json_request = test_base.json_request
json_request_return_dict = test_base.json_request_return_dict
request_html = test_base.request_html
BaseTestCase = test_base.BaseTestCase

NOTE_DAO = xutils.DAO("note")

from handlers.note.dao_api import NoteDao

def get_default_group_id():
    name = "default_group_id"
    note = get_by_name(xauth.current_name(), name)
    if note != None:
        return note.id
    return create_note_for_test("group", name)

def create_note_for_test(type, name, *, content = "", tags="", parent_id=0) -> int:
    assert type != None, "type cannot be None"
    assert name != None, "name cannot be None"
    assert isinstance(tags, str), "tags must be str"

    data = dict(name = name, type = type, content = content, tags=tags)

    if type != "group" and parent_id == 0:
        data["parent_id"] = str(get_default_group_id())

    if parent_id != 0:
        data["parent_id"] = str(parent_id)

    note_result = json_request_return_dict("/note/add", 
        method = "POST",
        data = data)
    
    note_id = note_result.get("id")
    print("新笔记id:", note_id)
    assert isinstance(note_id, int)
    return note_id

def delete_note_for_test(name):
    # 调用2次彻底删除
    user_id = xauth.current_user_id()
    note_index = note_dao.NoteIndexDao.get_by_name(creator_id=user_id, name=name)
    if note_index != None:
        dao_delete.delete_note_physically(note_index.creator, note_index.id)

def get_note_info(id):
    return get_by_id(id)

def delete_comment_for_test(id):
    json_request("/note/comment/delete", method = "POST", data = dict(comment_id = id))

def assert_json_request_success(test_case, url):
    result = json_request(url)
    test_case.assertEqual('success', result['code'])

class TestMain(BaseTestCase):

    def test_note_create_remove(self):
        self.check_200_debug("/note/recent_edit")
        delete_note_for_test("xnote-unit-test")
        delete_note_for_test("xnote-unit-test-copy")

        user_info = xauth.current_user()
        assert user_info != None
        
        group_id = get_default_group_id()
        file = json_request("/note/add", method="POST", 
            data=dict(name="xnote-unit-test", content="hello", parent_id = group_id))
        assert isinstance(file, dict)

        id = file["id"]
        note_info = NoteDao.get_by_id(id)
        assert note_info != None

        version = note_info.version
        assert isinstance(version, int)

        self.check_OK("/note/view?id=" + str(id))
        self.check_OK("/note/print?id=" + str(id))

        # 乐观锁更新
        resp = json_request_return_dict("/note/update", method="POST", 
            data=dict(id=id, content="new-content2", type="md", version=version, resp_type="json"))
        assert isinstance(resp, dict)

        self.assertEqual("success", resp["code"])

        resp = json_request_return_dict("/note/update", method="POST", 
            data=dict(id=id, content="new-content3", type="md", version=version+1, resp_type="json"))
        
        self.assertEqual("success", resp["code"])

        # 访问日志
        visit_note("test", id)
        
        # 普通更新
        resp = json_request_return_dict("/note/save", method="POST",
            data=dict(id=id, content="new-content", version=version+2, resp_type="json"))
        self.assertEqual("success", resp["code"])

        note_info = NoteDao.get_by_id(id)
        assert note_info != None

        self.assertEqual(note_info.content, "new-content")
        self.assertEqual(user_info.id, note_info.creator_id)
        
        # 第二次更新 使用新的api
        NoteDao.update_content(note_info, "new-content-2")
        note_info = NoteDao.get_by_id(id)
        assert note_info != None
        
        self.assertEqual(note_info.content, "new-content-2")

        # 复制笔记
        assert isinstance(note_info.name, str)
        copy_data = dict(name=note_info.name + "-copy", origin_id = note_info.id)
        resp = json_request_return_dict("/note/copy", method="POST", data=copy_data)
        print("copy resp:", resp)
        self.assertEqual("success", resp["code"])

        # 删除笔记
        json_request("/note/remove?id=" + str(id))
        note_info = NoteDao.get_by_id(id)
        assert note_info != None

        self.assertEqual(note_info.is_deleted, 1)

        # 恢复笔记
        json_request("/note/recover", method="POST", data=dict(id=id))
        note_info = NoteDao.get_by_id(id)
        assert note_info != None

        self.assertEqual(note_info.is_deleted, 0)

    def test_create_page(self):
        self.check_OK("/note/create")

    def test_create_name_empty(self):
        parent_id = get_default_group_id()
        result = json_request_return_dict("/note/create", method = "POST", data = dict(name = "", parent_id = parent_id))
        self.assertEqual(xutils.u('标题为空'), result['message'])

    def test_create_name_exits(self):
        delete_note_for_test("name-test")
        create_note_for_test("md", "name-test")

        result = json_request_return_dict("/note/create", method = "POST", data = dict(name = "name-test"))
        self.assertEqual(xutils.u('笔记【name-test】已存在'), result['message'])

        delete_note_for_test("name-test")

    def test_create_note_invalid_type(self):
        result = json_request_return_dict("/note/create", 
            method = "POST", 
            data = dict(type = "invalid", name = "invalid-test"))
        
        self.assertEqual(xutils.u("无效的类型: invalid"), result["message"])

    def test_note_group_add_view(self):
        delete_note_for_test("xnote-unit-group")
        group = json_request_return_dict("/note/add", method="POST",
            data = dict(name="xnote-unit-group", type="group"))
        id = group['id']
        self.check_OK('/note/view?id=%s' % id)
        json_request('/note/remove?id=%s' % id)

    def test_note_list_by_type(self):
        self.check_OK("/note/types")
        self.check_OK("/note/table")
        self.check_OK("/note/gallery")
        self.check_OK("/note/plan")
        self.check_OK("/note/list")
        self.check_OK("/note/html")

    def test_note_timeline(self):
        self.check_200("/note/timeline")
        self.check_200("/note/timeline?type=public")
        json_request("/note/timeline/month?year=2018&month=1")

    def test_timeline_api(self):
        default_group_id = get_default_group_id()
        assert_json_request_success(self, "/note/api/timeline")
        assert_json_request_success(self, "/note/api/timeline?type=public")
        assert_json_request_success(self, "/note/api/timeline?type=sticky")
        assert_json_request_success(self, "/note/api/timeline?type=removed")
        assert_json_request_success(self, "/note/api/timeline?type=archived")
        assert_json_request_success(self, "/note/api/timeline?type=all")
        assert_json_request_success(self, "/note/api/timeline?type=plan")
        assert_json_request_success(self, "/note/api/timeline?type=list")
        assert_json_request_success(self, "/note/api/timeline?type=gallery")
        assert_json_request_success(self, f"/note/api/timeline?type=default&parent_id={default_group_id}")
        assert_json_request_success(self, u"/note/api/timeline?type=search&key=xnote中文")

    def test_timeline_sort_func(self):
        build_date_result = xutils.Module("note").build_date_result
        note1 = Storage(name = "note1", ctime = "2015-01-01 00:00:00")
        note2 = Storage(name = "note2", ctime = "2015-06-01 00:00:00")
        note3 = Storage(name = "note3", ctime = "2014-01-01 00:00:00")
        result = build_date_result([note1, note2, note3])

        self.assertEqual("success", result['code'])
        self.assertEqual("2015-06-01", result['data'][0]['title'])
        self.assertEqual("2015-01-01", result['data'][1]['title'])
        self.assertEqual("2014-01-01", result['data'][2]['title'])

    def test_note_editor_md(self):
        group_id = get_default_group_id()
        delete_note_for_test("xnote-md-test")
        
        file = json_request("/note/add", method="POST",
            data=dict(name="xnote-md-test", type="md", content="hello markdown", parent_id = group_id))
        
        id = file["id"]
        file = json_request("/note/view?id=%s&_format=json" % id).get("file")
        self.assertEqual("md", file["type"])
        self.assertEqual("hello markdown", file["content"])
        self.check_200("/note/edit?id=%s" % id)
        self.check_OK("/note/history?id=%s" % id)

        json_request("/note/history_view?id=%s&version=%s" % (file["id"], file["version"]))
        json_request("/note/remove?id=%s" % id)

    def test_note_editor_html(self):
        delete_note_for_test("xnote-html-test")

        id = create_note_for_test("html", "xnote-html-test", content = "test")
        note_info = NoteDao.get_by_id(id)
        
        self.assertTrue(id != "")
        print("id=%s" % id)

        save_data = dict(id=id, type="html", data="<p>hello</p>", version = note_info.version)
        resp = json_request("/note/save", method="POST", data = save_data)
        self.assertEqual("success", resp["code"])

        file = json_request("/note/view?id=%s&_format=json" % id).get("file")
        self.assertEqual("html", file["type"])
        self.assertEqual("<p>hello</p>", file["data"])

        if xutils.bs4 != None:
            self.assertEqual("hello", file["content"])
        
        self.check_200("/note/edit?id=%s"%id)
        json_request("/note/remove?id=%s" % id)

    def test_note_group(self):
        self.check_200("/note/group")
        self.check_200("/note/ungrouped")
        self.check_200("/note/public")
        self.check_200("/note/removed")
        self.check_200("/note/recent_edit")
        self.check_200("/note/recent_created")
        self.check_200("/note/group/select")
        self.check_200("/note/group/select?id=1234")
        self.check_200("/note/date?year=2019&month=1")
        self.check_200("/note/sticky")

    def test_note_share(self):
        delete_note_for_test("xnote-share-test")

        id = create_note_for_test("md", "xnote-share-test", content = "hello")

        self.check_OK("/note/share?id=" + str(id))
        file = json_request_return_dict("/note/view?id=%s&_format=json" % id).get("file")
        assert file != None
        self.assertEqual(1, file["is_public"])
        
        # 登出后可以搜索到
        logout_test_user()
        try:
            result = note_dao.search_name(words=["share"])
            assert len(result) > 0
            assert result[0].name == "xnote-share-test"
        finally:
            login_test_user()
        
        
        cancel_result = json_request_return_dict("/note/share/cancel?id=" + str(id))
        assert cancel_result.get("success", False)
        
        file = json_request_return_dict("/note/view?id=%s&_format=json" % id).get("file")
        assert file != None
        self.assertEqual(0, file["is_public"])

        logout_test_user()
        try:
            # 登出后无法访问
            self.check_303("/note/view/%s" % id)
            
            # 登出后无法搜索到数据
            result = note_dao.search_name(["share"])
            assert len(result) == 0
            
            # clean up
            json_request(f"/note/remove?id={id}")
        finally:
            login_test_user()

    def test_note_share_to(self):
        """分享给指定用户"""
        delete_note_for_test("xnote-share-test")
        id = create_note_for_test("md", "xnote-share-test", content = "hello")

        share_resp = json_request_return_dict("/note/share", method="POST",
            data=dict(id=id, share_to="test2"))
        print("share_resp:", share_resp)
        self.assertEqual("success", share_resp["code"])

        delete_share_resp = json_request_return_dict("/note/share/cancel", method="POST",
            data=dict(id=id, share_to="test2"))
        
        print("delete_share_resp:", delete_share_resp)
        self.assertEqual("success", delete_share_resp["code"])
        self.check_OK("/note/share_to_me")
        
    def test_note_share_group_to(self):
        """分享笔记本"""
        delete_note_for_test("xnote-share-group")
        delete_note_for_test("xnote-share-group-child")
        delete_note_for_test("xnote-private-group")
        
        target_user = "test2"
        group_id = create_note_for_test("group", "xnote-share-group")
        assert group_id > 0
        note_id = create_note_for_test("md", "xnote-share-group-child", content = "child content", parent_id=group_id)
        assert note_id > 0
        
        # 创建一个对照组，无授权
        unauthorized_id = create_note_for_test("group", "xnote-private-group")
        assert unauthorized_id > 0
        
        share_resp = json_request_return_dict("/note/share", method="POST",
            data=dict(id=group_id, share_to=target_user))
        print("share_resp:", share_resp)
        
        try:
            login_test_user(target_user)
            assert xauth.current_name_str() == target_user
            result = json_request_return_dict(f"/note/api/timeline?_type=json&type=default&parent_id={group_id}")
            data = result.get("data", [])
            assert len(data) == 1
            
            no_auth_result = json_request_return_dict(f"/note/api/timeline?_type=json&type=default&parent_id={unauthorized_id}")
            result_code = no_auth_result.get("code", "")
            assert result_code == "403"
        finally:
            login_test_user()

    def test_link_share(self):
        delete_note_for_test("xnote-link-share-test")
        note_id = create_note_for_test(name = "xnote-link-share-test", type = "md")
        resp = json_request_return_dict("/note/link_share", method = "POST", data = dict(id = note_id))
        self.assertEqual("success", resp["code"])

    def test_note_tag(self):
        delete_note_for_test("xnote-tag-test")
        id = create_note_for_test("md", "xnote-tag-test", content = "hello", tags="ABC DEF ABC")

        note_info = note_dao.get_by_id(id)
        assert note_info != None

        self.assertEqual(note_info.tags, ["ABC", "DEF"])

        from xnote.service import TagBindService, TagTypeEnum
        user_info = xauth.current_user()
        assert user_info != None

        service = TagBindService(TagTypeEnum.note_tag)
        binds = service.get_by_target_id(user_id=user_info.id, target_id=int(note_info.id))
        tags = [x.tag_code for x in binds]
        assert len(binds) == 2
        assert "abc" in tags
        assert "def" in tags

        # clean up
        json_request("/note/remove?id=%s" % id)
    
    def test_note_tag_meta_create(self):
        from handlers.note.dao_tag import TagMetaDao
        create_params = dict(
            tag_type = "group",
            tag_name = "测试"
        )
        result = json_request_return_dict("/note/tag/create", method="POST", data = create_params)
        self.assertEqual("success", result["code"])

        meta_info = TagMetaDao.get_by_name(xauth.current_name(), "测试", tag_type="group")
        assert meta_info != None

        self.assertEqual("测试", meta_info.tag_name)
        self.assertEqual("group", meta_info.tag_type)

    def test_note_stick(self):
        delete_note_for_test("xnote-share-test")

        id = create_note_for_test("md", "xnote-share-test", content = "hello")

        self.check_OK("/note/stick?id=%s" % id)
        self.check_OK("/note/unstick?id=%s" % id)

        # clean up
        json_request("/note/remove?id=" + str(id))


    def test_note_comment(self):
        # clean comments
        data = json_request("/note/comments?note_id=123")
        for comment in data:
            delete_comment_for_test(comment['id'])

        # 创建一个评论
        request = dict(note_id = "123", content = "hello")
        json_request("/note/comment/save", method="POST", data = request)

        # 查询评论
        data = json_request("/note/comments?note_id=123")
        self.assertEqual(1, len(data))
        self.assertEqual("hello", data[0]['content'])

        comment_id = data[0]["id"]

        # 获取编辑对话框
        self.check_OK("/note/comment?comment_id=%s&p=edit" % comment_id)

        # 更新评论
        data = json_request("/note/comment?comment_id=%s&p=update&content=%s" % (comment_id, "#TOPIC# hello"))
        self.assertEqual("success", data["code"])

        # 查询用户维度评论列表
        data = json_request("/note/comment/list?list_type=user")
        self.assertEqual(1, len(data))

        # 我的所有评论
        self.check_OK("/note/comment/mine")

        # 搜索评论
        from handlers.note.comment import search_comment_detail, search_comment_summary
        ctx = Storage(user_name = xauth.current_name(), 
            key = "hello", 
            words = ["hello"], 
            messages = [])
        summary_ctx = copy.deepcopy(ctx)

        search_comment_detail(ctx)
        self.assertEqual(1, len(ctx.messages))

        search_comment_summary(summary_ctx)
        
        print("搜索评论汇总结果:", summary_ctx)

        self.assertEqual(1, len(summary_ctx.messages))


        # 删除评论
        result = json_request("/note/comment/delete", method = "POST", 
            data = dict(comment_id = comment_id))
        self.assertEqual("success", result["code"])

        data = json_request("/note/comment/list?list_type=user")
        self.assertEqual(0, len(data))


    def test_note_management(self):
        self.check_OK("/note/management?parent_id=0")
        self.check_404("/note/management?parent_id=123")

    def test_gallery_view(self):
        delete_note_for_test("gallery-test")
        id = create_note_for_test("gallery", "gallery-test")

        self.check_OK("/note/%s" % id)

    def test_gallery_manage(self):
        delete_note_for_test("gallery-test")
        id = create_note_for_test("gallery", "gallery-test")
        self.check_200_debug("/note/management?parent_id=%s" % id)

    def test_text_view(self):
        delete_note_for_test("text-test")
        id = create_note_for_test("md", "text-test")

        self.check_OK("/note/%s" % id)

    def test_note_category(self):
        self.check_OK("/note/category")

    def test_archive(self):
        delete_note_for_test("archive-test")
        id = create_note_for_test("group", "archive-test")
        self.check_OK("/note/archive?id=%s" % id)
        note_info = get_note_info(id)
        self.assertEqual(True, note_info.archived)

        # 取消归档
        self.check_OK("/note/unarchive?id=%s" % id)
        note_info = get_note_info(id)
        self.assertEqual(False, note_info.archived)

    def test_move(self):
        delete_note_for_test("move-test")
        delete_note_for_test("move-group-test")

        id = create_note_for_test("md", "move-test")
        parent_id = create_note_for_test("group", "move-group-test")

        json_request("/note/move?id=%s&parent_id=%s" % (id, parent_id))
        group_info = get_note_info(parent_id)
        assert group_info != None
        self.assertEqual(1, group_info.children_count)

    def test_rename(self):
        delete_note_for_test("rename-test")
        delete_note_for_test("newname-test")

        id = create_note_for_test("md", "rename-test")
        json_request("/note/rename", method = "POST", data = dict(id = id, name = "newname-test"))

        note_info = get_note_info(id)
        self.assertEqual("newname-test", note_info.name)

    def test_stat(self):
        self.check_OK("/note/stat")

    def test_note_search(self):
        assert_json_request_success(self, u"/note/api/timeline?type=search&key=xnote中文")
        self.check_OK(u"/search?key=test中文&category=content")

    def test_split_words(self):
        from xutils.textutil import split_words
        words = split_words(u"mac网络")
        self.assertEqual(["mac", u"网", u"络"], words)

        words = split_words(u"网络mac")
        self.assertEqual([u"网", u"络", "mac"], words)

        words = split_words(u"网mac络")
        self.assertEqual([u"网", u"mac", u"络"], words)

    def test_recent(self):
        self.check_OK("/note/recent?orderby=view")
        self.check_OK("/note/recent?orderby=update")
        self.check_OK("/note/recent?orderby=create")

    def a_test_recent_files(self):
        json_data = json_request("/note/recent_edit")
        files = json_data["files"]
        print("files=%s" % len(files))

    def test_note_api_group(self):
        json_data = json_request_return_dict("/note/api/group?list_type=all")
        self.assertEqual("success", json_data["code"])

    def test_workspace(self):
        self.check_OK("/note/workspace")

    # def test_view_by_skey(self):
    #     self.check_OK("/note/view?skey=skey_test")
    #     note = get_by_user_skey(xauth.current_name(), "skey_test")
    #     self.assertTrue(note != None)
    #     delete_note_for_test("skey_test")

    def test_import_from_html(self):
        html = """<html>
        <title>MyTitle</title>
        <body>
            <h1>Head1</h1>
            <p>Text</p>
        </body>
        </html>"""
        result = html_importer.import_from_html(html)

        print(result)

        self.assertEqual("MyTitle", result.title)
        self.assertTrue(result.texts[0].find("# Head1") >= 0)

    def test_get_dialog(self):
        delete_note_for_test("xnote-dialog-group")

        note_id = create_note_for_test("group", "xnote-dialog-group")

        self.check_OK("/note/ajax/group_option_dialog?note_id=%s" % note_id)
        self.check_OK("/note/ajax/share_group_dialog?note_id=%s"  % note_id)
        self.check_OK("/note/ajax/edit_symbol_dialog")


    def test_lock_success(self):
        note_id = "001"
        token = textutil.create_uuid()

        r1 = NOTE_DAO.refresh_edit_lock(note_id, token, time.time() + 60)
        self.assertTrue(r1)

        r2 = NOTE_DAO.refresh_edit_lock(note_id, token, time.time() + 60)
        self.assertTrue(r2)


    def test_lock_conflict(self):
        note_id = "002"
        token1 = textutil.create_uuid()
        token2 = textutil.create_uuid()

        r1 = NOTE_DAO.refresh_edit_lock(note_id, token1, time.time() + 60)
        self.assertTrue(r1)

        r2 = NOTE_DAO.refresh_edit_lock(note_id, token2, time.time() + 60)
        self.assertFalse(r2)


    def test_log_list_recent_events(self):
        from handlers.note.dao_log import list_recent_events
        events = list_recent_events("test")
        self.assertTrue(len(events) > 0)
    
    def test_get_note_depth(self):
        from handlers.note.dao import get_by_id
        from handlers.note.dao_read import get_note_depth
        note_id = create_note_for_test("group", "test-get-note-depth")
        note_info = get_by_id(note_id)
        note_depth = get_note_depth(note_info)
        self.assertEqual(1, note_depth)
    
    def test_check_and_create_default_book(self):
        from handlers.note.dao_book import check_and_create_default_book
        check_and_create_default_book("test")


    def test_note_visit(self):
        from handlers.note.dao import visit_note
        from handlers.note.dao_log import list_most_visited

        delete_note_for_test("visit-test")

        note_id = create_note_for_test("md", "visit-test")

        for i in range(100):
            visit_note(xauth.current_name(), note_id)

        recent_notes = list_most_visited(xauth.current_name(), 0, 20)

        print("recent_notes", recent_notes)

        self.assertTrue(len(recent_notes) > 0)
        self.assertEqual(recent_notes[0].badge_info, "100")


    def test_comment_search(self):
        from handlers.note.dao_comment import CommentDO
        note_id = create_note_for_test("list", "check-list-test")

        user_info = xauth.current_user()
        assert user_info != None

        comment = CommentDO()
        comment.user = user_info.name
        comment.user_id = user_info.id
        comment.type = "list_item"
        comment.note_id = note_id
        comment.content = "test comment search"

        dao_comment.create_comment(comment)
        self.check_200("/note/comments?note_id=%s&list_type=search&key=test&resp_type=html&page=1" % note_id)

        comment_list = self.json_request("/note/comments?note_id=%s&list_type=search&key=test&page=1" % note_id)
        assert isinstance(comment_list, list)
        assert len(comment_list) > 0

        # 删除comment
        for item in comment_list:
            dao_comment.delete_comment(item["id"])
        
        dao_delete.delete_note(note_id)
        

    def test_append_tag(self):
        note_id = create_note_for_test("md", "bind-tag-test")
        dao_tag.append_tag(note_id, "$todo$")
        note_info = note_dao.get_by_id(note_id)
        assert note_info != None
        assert isinstance(note_info.tags, list)
        self.assertEqual(note_info.tags, ["$todo$"])
        delete_note_for_test("bind-tag-test")

    def test_group_manage(self):
        delete_note_for_test("group-manage-test")
        note_id = create_note_for_test("group", "group-manage-test")
        self.check_OK(f"/note/manage?parent_id={note_id}")

    def test_month_plan(self):
        from handlers.plan.dao import MonthPlanDao

        delete_note_for_test("plan-test")
        note_id = create_note_for_test("md", "plan-test")
        user_info = xauth.current_user()
        assert user_info != None
        month = time.strftime("%Y-%m")
        plan_record = MonthPlanDao.get_or_create(user_info, month)
        plan_id = plan_record._id
        json_request_return_dict("/plan/month/add", method="POST", data=dict(id=plan_id, note_ids=str(note_id)))
        self.check_OK("/plan/month")

    def test_touch_note(self):
        delete_note_for_test("touch-test")
        note_id = create_note_for_test("md", "touch-test")
        self.check_OK(f"/note/touch?id={note_id}&resp_type=json")

    def test_update_level(self):
        delete_note_for_test("status-test")
        note_id = create_note_for_test("md", "status-test")
        resp = self.json_request_return_dict(f"/note/status", method="POST", data=dict(id=note_id, status=1))
        self.assertTrue(resp["success"])

        note_info = note_dao.get_by_id(note_id)
        assert note_info != None
        assert note_info.level == 1
    
    def test_checklist_search(self):
        delete_note_for_test("checklist-test")
        note_id = create_note_for_test("list", "checklist-test")
        from handlers.note.dao_comment import CommentDao, CommentDO
        comment = CommentDO()
        comment.type = "list_item"
        comment.content = "comment content"
        comment.user_id = xauth.current_user_id()
        comment.note_id = note_id
        comment_id = CommentDao.create(comment)
        
        self.check_OK(f"/note/checklist/search?note_id={note_id}")

        CommentDao.delete_by_id(comment_id)
        
    def test_note_tag_v2(self):
        delete_note_for_test("tag-test")
        create_note_for_test("list", "tag-test", tags="tag1 tag2")
        
        dict = self.json_request_return_dict("/note/tag/list?tag_type=note&group_id=1&v=2")
        assert dict["success"] == True
        assert len(dict["data"]["all_list"]) > 0

