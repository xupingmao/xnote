# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/10/05 20:23:43
# @modified 2019/10/05 21:05:22
import xutils

# cannot perform relative import
try:
    import test_base
except ImportError:
    from tests import test_base

from handlers.note.dao import delete_comment

app          = test_base.init()
json_request = test_base.json_request
request_html = test_base.request_html
BaseTestCase = test_base.BaseTestCase

class TestMain(BaseTestCase):

    def test_note_add_remove(self):
        self.check_200("/note/recent_edit")
        json_request("/note/remove?name=xnote-unit-test")
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
        
        # 普通更新
        json_request("/note/save", method="POST",
            data=dict(id=id, content="new-content"))
        json_request("/note/remove?id=" + str(id))

    def test_note_group_add_view(self):
        group = json_request("/note/add", method="POST",
            data = dict(name="xnote-unit-group", type="group"))
        id = group['id']
        self.check_OK('/note/view?id=%s' % id)
        json_request('/note/remove?id=%s' % id)

    def test_note_list_by_type(self):
        self.check_OK("/note/types")
        self.check_OK("/note/table")
        self.check_OK("/note/gallery")

    def test_note_notice(self):
        self.check_OK("/note/notice")

    def test_note_timeline(self):
        self.check_200("/note/timeline")

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

        # clean up
        json_request("/note/remove?id=" + str(id))

    def test_file_timeline(self):
        json_request("/note/timeline")
        json_request("/note/timeline/month?year=2018&month=1")

    def test_note_tag(self):
        json_request("/note/remove?name=xnote-tag-test")
        file = json_request("/note/add", method="POST", 
            data=dict(name="xnote-tag-test", content="hello"))
        id = file["id"]
        json_request("/note/tag/update", method="POST", data=dict(file_id=id, tags="ABC DEF"))
        json_request("/note/tag/%s" % id)
        json_request("/note/tag/update", method="POST", data=dict(file_id=id, tags=""))

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
            delete_comment(comment['id'])

        # test flow
        json_request("/note/comment/save", method="POST", data = dict(note_id = "123", content = "hello"))
        data = json_request("/note/comments?note_id=123")
        self.assertEqual(1, len(data))
        self.assertEqual("hello", data[0]['content'])

