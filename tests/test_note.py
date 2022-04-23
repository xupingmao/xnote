# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/10/05 20:23:43
# @modified 2022/04/23 10:54:57
# @filename test_note.py

import logging
import time
import copy

import xutils
# cannot perform relative import
try:
    import test_base
    from test_base import login_test_user, logout_test_user
except ImportError:
    from tests import test_base
    from tests.test_base import login_test_user, logout_test_user

import xauth

from handlers.note.dao import get_by_id, visit_note, get_by_user_skey
from xutils import Storage
from xutils import textutil

app          = test_base.init()
json_request = test_base.json_request
request_html = test_base.request_html
BaseTestCase = test_base.BaseTestCase

NOTE_DAO = xutils.DAO("note")

def create_note_for_test(type, name):
    assert type != None, "type cannot be None"
    assert name != None, "name cannot be None"

    data = dict(name = name, type = type, content = "hello,world")
    file = json_request("/note/add", 
        method = "POST",
        data = data)
    return file["id"]

def delete_note_for_test(name):
    json_request("/note/remove?name=%s" % name)

def get_note_info(id):
    return get_by_id(id)

def delete_comment_for_test(id):
    json_request("/note/comment/delete", method = "POST", data = dict(comment_id = id))

def assert_json_request_success(test_case, url):
    result = json_request(url)
    test_case.assertEqual('success', result['code'])

class TestMain(BaseTestCase):

    def test_note_add_remove(self):
        self.check_200_debug("/note/recent_edit")
        delete_note_for_test("xnote-unit-test")

        file = json_request("/note/add", method="POST", 
            data=dict(name="xnote-unit-test", content="hello"))
        id = file["id"]
        self.check_OK("/note/view?id=" + str(id))
        self.check_OK("/note/print?id=" + str(id))

        # 乐观锁更新
        json_request("/note/update", method="POST", 
            data=dict(id=id, content="new-content2", type="md", version=0))
        json_request("/note/update", method="POST", 
            data=dict(id=id, content="new-content3", type="md", version=1))

        # 访问日志
        visit_note("test", id)
        
        # 普通更新
        json_request("/note/save", method="POST",
            data=dict(id=id, content="new-content"))
        json_request("/note/remove?id=" + str(id))

    def test_create_page(self):
        self.check_OK("/note/create")

    def test_create_name_empty(self):
        result = json_request("/note/create", method = "POST", data = dict(name = ""))
        self.assertEqual(xutils.u('标题为空'), result['message'])

    def test_create_name_exits(self):
        delete_note_for_test("name-test")
        create_note_for_test("md", "name-test")

        result = json_request("/note/create", method = "POST", data = dict(name = "name-test"))
        self.assertEqual(xutils.u('笔记【name-test】已存在'), result['message'])

        delete_note_for_test("name-test")

    def test_create_note_invalid_type(self):
        result = json_request("/note/create", 
            method = "POST", 
            data = dict(type = "invalid", name = "invalid-test"))
        
        self.assertEqual(xutils.u("无效的类型: invalid"), result["message"])

    def test_note_group_add_view(self):
        delete_note_for_test("xnote-unit-group")
        group = json_request("/note/add", method="POST",
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
        assert_json_request_success(self, "/note/api/timeline")
        assert_json_request_success(self, "/note/api/timeline?type=public")
        assert_json_request_success(self, "/note/api/timeline?type=sticky")
        assert_json_request_success(self, "/note/api/timeline?type=removed")
        assert_json_request_success(self, "/note/api/timeline?type=archived")
        assert_json_request_success(self, "/note/api/timeline?type=all")
        assert_json_request_success(self, "/note/api/timeline?type=plan")
        assert_json_request_success(self, "/note/api/timeline?type=list")
        assert_json_request_success(self, "/note/api/timeline?type=gallery")
        assert_json_request_success(self, u"/note/api/timeline?type=default&parent_id=012345")
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
        json_request("/note/remove?name=xnote-md-test")
        file = json_request("/note/add", method="POST",
            data=dict(name="xnote-md-test", type="md", content="hello markdown"))
        id = file["id"]
        file = json_request("/note/view?id=%s&_format=json" % id).get("file")
        self.assertEqual("md", file["type"])
        self.assertEqual("hello markdown", file["content"])
        self.check_200("/note/edit?id=%s" % id)
        self.check_OK("/note/history?id=%s" % id)
        json_request("/note/history_view?id=%s&version=%s" % (file["id"], file["version"]))
        json_request("/note/remove?id=%s" % id)

    def test_note_editor_html(self):
        json_request("/note/remove?name=xnote-html-test")
        file = json_request("/note/add", method="POST",
            data=dict(name="xnote-html-test", type="html"))
        id = file["id"]
        self.assertTrue(id != "")
        print("id=%s" % id)
        json_request("/note/save", method="POST", data=dict(id=id, type="html", data="<p>hello</p>"))
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
        json_request("/note/remove?name=xnote-share-test")
        file = json_request("/note/add", method="POST", 
            data=dict(name="xnote-share-test", content="hello"))
        id = file["id"]
        self.check_OK("/note/share?id=" + str(id))
        file = json_request("/note/view?id=%s&_format=json" % id).get("file")
        self.assertEqual(1, file["is_public"])
        
        self.check_OK("/note/share/cancel?id=" + str(id))
        file = json_request("/note/view?id=%s&_format=json" % id).get("file")
        self.assertEqual(0, file["is_public"])

        logout_test_user()
        self.check_OK("/note/view/%s" % id)

        # clean up
        json_request("/note/remove?id=" + str(id))
        login_test_user()

    def test_note_share_to(self):
        delete_note_for_test("xnote-share-test")
        note = json_request("/note/add", method="POST", 
            data=dict(name="xnote-share-test", content="hello"))
        id = note["id"]
        share_resp = json_request("/note/share", method="POST",
            data=dict(id=id, share_to="test2"))
        logging.info("share_resp:%s", share_resp)
        self.assertEqual("success", share_resp["code"])

        delete_share_resp = json_request("/note/share/cancel", method="POST",
            data=dict(id=id, share_to="test2"))
        
        logging.info("delete_share_resp:%s", delete_share_resp)
        self.assertEqual("success", delete_share_resp["code"])

    def test_link_share(self):
        delete_note_for_test("xnote-link-share-test")
        note_id = create_note_for_test(name = "xnote-link-share-test", type = "md")
        resp = json_request("/note/link_share", method = "POST", data = dict(id = note_id))
        self.assertEqual("success", resp["code"])

    def test_note_tag(self):
        json_request("/note/remove?name=xnote-tag-test")
        note = json_request("/note/add", method="POST", 
            data=dict(name="xnote-tag-test", content="hello"))
        print("created note:", note)
        id = note["id"]
        json_request("/note/tag/update", method="POST", data=dict(file_id=id, tags="ABC DEF"))
        json_request("/note/tag/%s" % id)
        json_request("/note/tag/update", method="POST", data=dict(file_id=id, tags=""))

        # clean up
        json_request("/note/remove?id=%s" % id)

    def test_note_stick(self):
        json_request("/note/remove?name=xnote-share-test")
        file = json_request("/note/add", method="POST", 
            data=dict(name="xnote-share-test", content="hello"))
        id = file["id"]

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

    def test_gallery_management(self):
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

        id = create_note_for_test("group", "move-test")
        parent_id = create_note_for_test("group", "move-group-test")

        json_request("/note/move?id=%s&parent_id=%s" % (id, parent_id))
        group_info = get_note_info(parent_id)
        self.assertEqual(1, group_info.size)

    def test_rename(self):
        delete_note_for_test("rename-test")
        delete_note_for_test("newname-test")

        id = create_note_for_test("md", "rename-test")
        json_request("/note/rename", method = "POST", data = dict(id = id, name = "newname-test"))

        note_info = get_note_info(id)
        self.assertEqual("newname-test", note_info.name)

    def test_stat(self):
        self.check_OK("/note/stat")

    def test_dict(self):
        json_request("/dict/edit/name", method = "POST", data = dict(name = "name", value = u"姓名".encode("utf-8")))
        self.check_OK("/note/dict")
        self.check_OK("/dict/search?key=name")

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
        json_data = json_request("/note/api/group")
        self.assertEqual("success", json_data["code"])

    def test_workspace(self):
        self.check_OK("/note/workspace")

    def test_view_by_skey(self):
        self.check_OK("/note/view?skey=skey_test")

        note = get_by_user_skey(xauth.current_name(), "skey_test")
        self.assertTrue(note != None)

        delete_note_for_test("skey_test")

    def test_import_from_html(self):
        html = """<html>
        <title>MyTitle</title>
        <body>
            <h1>Head1</h1>
            <p>Text</p>
        </body>
        </html>"""
        result = NOTE_DAO.import_from_html(html)

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


