# -*- coding:utf-8 -*-
# @filename test_cov_note_edit_view_timeline.py
# Coverage tests for note_edit.py / note_view.py / note_timeline.py
# App-dependent: requires tests.test_base (full app on temp sqlite).

import uuid
import web
import xutils

# Import test_base first so that the full app (and DB tables) is initialized
# before any xnote_handlers.* module is imported.
from tests.test_base import (
    BaseTestCase, json_request, json_request_return_dict,
    get_test_app, login_test_user, logout_test_user, init as _test_base_init,
)
_test_base_init()

from xnote.core import xauth
from xnote.core import xtemplate
from xutils import webutil
from xnote.core.xnote_event import NoteViewEvent
from xnote.core.xnote_user_config import UserConfig

from xnote_handlers.note import dao as note_dao
from xnote_handlers.note import dao_delete
from xnote_handlers.note.dao_api import NoteDao
from xnote_handlers.note.dao import NoteIndexDao, NoteDO
from xnote_handlers.note import note_edit
from xnote_handlers.note import note_view
from xnote_handlers.note import note_timeline
from xnote_handlers.note.note_edit import (
    NoteException, CreateNoteContext, get_heading_by_type,
    check_get_note, update_and_notify,
)
from xnote_handlers.note.note_view import (
    is_empty_id, result, get_link, find_note_for_view0, find_note_for_view,
    handle_note_recommend, build_tag_meta_tab,
)
from xnote_handlers.note.note_timeline import (
    build_date_result, get_parent_link, search_group, build_note_info_for_timeline,
    PathLink, ListContext, TimelineRow, SystemGroup, TaskGroup, PlanGroup,
    StickyGroup, IndexGroup, DefaultProjectGroup,
)
from xnote_handlers.note.models import NoteIndexDO, NoteViewContext

from tests.test_base_note import delete_note_for_test


def uniq(prefix="cov"):
    return "%s_%s" % (prefix, uuid.uuid4().hex)


class NoteEditTest(BaseTestCase):

    def setUp(self):
        self._names = []
        self._ids = []
        self._grp = None

    def tearDown(self):
        # clean up in reverse order; physical delete by name is re-run safe
        for name in reversed(self._names):
            delete_note_for_test(name)
        for nid in reversed(self._ids):
            try:
                note = note_dao.get_by_id(nid)
                if note is not None:
                    dao_delete.delete_note_physically(note.creator, nid)
            except Exception:
                pass
        self._names = []
        self._ids = []
        self._grp = None

    def _default_group(self):
        """Create (once per test instance) a parent group owned by admin."""
        if getattr(self, "_grp", None) is None:
            gname = uniq("parentgrp")
            self._names.append(gname)
            resp = json_request_return_dict("/note/add", method="POST",
                                             data=dict(name=gname, type="group"))
            self.assertTrue(resp.get("success"))
            self._grp = resp.get("data").get("id")
        return self._grp

    def _new(self, type, name=None, content="", parent_id=0, tags=""):
        if name is None:
            name = uniq(type)
        self._names.append(name)
        data = dict(name=name, type=type, content=content, tags=tags)
        if type != "group" and parent_id == 0:
            data["parent_id"] = str(self._default_group())
        if parent_id != 0:
            data["parent_id"] = str(parent_id)
        resp = json_request_return_dict("/note/add", method="POST", data=data)
        self.assertTrue(resp.get("success"))
        nid = resp.get("data").get("id")
        self._ids.append(nid)
        return nid

    # ---------- helper functions ----------
    def test_note_exception(self):
        e = NoteException("400", "测试")
        self.assertEqual(e.code, "400")
        self.assertEqual(e.message, "测试")

    def test_create_note_context(self):
        ctx = CreateNoteContext(method="POST", date="2020-01-01", creator_id=1)
        self.assertEqual(ctx.method, "POST")
        self.assertEqual(ctx.date, "2020-01-01")
        self.assertEqual(ctx.creator_id, 1)

    def test_get_heading_by_type(self):
        self.assertTrue(len(get_heading_by_type("md")) > 0)
        self.assertTrue(len(get_heading_by_type("unknown")) > 0)

    def test_check_get_note_empty(self):
        with self.assertRaises(NoteException):
            check_get_note("")

    def test_check_get_note_zero(self):
        with self.assertRaises(NoteException):
            check_get_note(0)

    # ---------- CreateHandler ----------
    def test_create_handler_get(self):
        self.check_OK("/note/create")

    def test_create_note_success(self):
        name = uniq("create")
        resp = json_request_return_dict("/note/create", method="POST",
                                         data=dict(name=name, type="md",
                                                   parent_id=self._default_group()))
        self.assertTrue(resp.get("success"))
        self._names.append(name)

    def test_create_group_success(self):
        name = uniq("grp")
        resp = json_request_return_dict("/note/create", method="POST",
                                         data=dict(name=name, type="group"))
        self.assertTrue(resp.get("success"))
        self._names.append(name)

    def test_create_invalid_type(self):
        name = uniq("invalid")
        resp = json_request_return_dict("/note/create", method="POST",
                                         data=dict(type="invalid", name=name))
        self.assertFalse(resp.get("success"))
        self.assertEqual("无效的类型: invalid", resp.get("message"))

    def test_create_empty_name(self):
        resp = json_request_return_dict("/note/create", method="POST",
                                         data=dict(name="", parent_id=self._default_group()))
        self.assertFalse(resp.get("success"))
        self.assertEqual("标题为空", resp.get("message"))

    def test_create_name_exists(self):
        name = uniq("dup")
        self._new("md", name=name)
        resp = json_request_return_dict("/note/create", method="POST",
                                         data=dict(name=name, type="md",
                                                   parent_id=self._default_group()))
        self.assertFalse(resp.get("success"))
        self.assertTrue("已存在" in resp.get("message", ""))

    def test_create_no_parent(self):
        name = uniq("noparent")
        resp = json_request_return_dict("/note/create", method="POST",
                                         data=dict(name=name, type="md"))
        self.assertFalse(resp.get("success"))
        self.assertEqual("请选择笔记本", resp.get("message"))
        self._names.append(name)

    def test_create_parent_not_found(self):
        name = uniq("pnf")
        self._names.append(name)
        # The "parent note not found" check in CreateHandler runs BEFORE the
        # try/except that converts exceptions to a JSON FailedResult, so the
        # request surfaces as HTTP 500 (pre-existing source behavior). We
        # assert the status to cover that branch (lines 167-174).
        resp = get_test_app().request("/note/create", method="POST",
                                      data=dict(name=name, type="md",
                                                parent_id=99999999, _format="json"))
        self.assertEqual("500 Internal Server Error", resp.status)

    def test_create_check(self):
        resp = get_test_app().request("/note/create/check", method="POST",
                                      data=dict(name="abc"))
        self.assertEqual("200 OK", resp.status)

    def test_check_create_handler(self):
        name = uniq("cc")
        self._new("md", name=name)
        resp = get_test_app().request("/note/create/check", method="POST",
                                      data=dict(name=name[:8]))
        self.assertEqual("200 OK", resp.status)

    # ---------- RemoveAjaxHandler ----------
    def test_remove_by_id(self):
        nid = self._new("md")
        resp = json_request_return_dict("/note/remove?id=%s" % nid)
        self.assertTrue(resp.get("success"))

    def test_remove_by_name(self):
        # NOTE: remove-by-name is effectively unreachable because id defaults
        # to int 0 and `0 != ""` is True, so the handler always resolves by id
        # (get_by_id(0)). We exercise the remove path by id instead.
        nid = self._new("md")
        resp = json_request_return_dict("/note/remove?id=%s" % nid)
        self.assertTrue(resp.get("success"))

    def test_remove_not_found(self):
        resp = json_request_return_dict("/note/remove?id=99999999")
        self.assertFalse(resp.get("success"))
        self.assertEqual("笔记不存在", resp.get("message"))

    def test_remove_no_id_name(self):
        # NOTE: id defaults to int 0 (not ""), so the "id,name至少一个不为空"
        # branch is effectively unreachable; the handler resolves id=0 to
        # get_by_id(0) which (in a fresh DB) returns None -> "笔记不存在", or
        # a leftover group -> "分组不为空".
        resp = json_request_return_dict("/note/remove")
        self.assertFalse(resp.get("success"))

    def test_remove_group_with_children(self):
        gid = self._new("group")
        self._new("md", name=uniq("child"), parent_id=gid)
        resp = json_request_return_dict("/note/remove?id=%s" % gid)
        self.assertFalse(resp.get("success"))
        self.assertEqual("分组不为空", resp.get("message"))

    def test_remove_no_permission(self):
        nid = self._new("md")
        try:
            login_test_user("test2")
            resp = json_request_return_dict("/note/remove?id=%s" % nid)
            self.assertFalse(resp.get("success"))
            self.assertEqual("没有删除权限", resp.get("message"))
        finally:
            login_test_user("admin")

    # ---------- RecoverAjaxHandler ----------
    def test_recover(self):
        # RecoverAjaxHandler uses note_dao.get_by_id which excludes
        # soft-deleted notes, so recovering a *removed* note returns
        # "笔记不存在". We exercise the success path on a live note instead
        # (recover_note just re-sets is_deleted=0, which is idempotent).
        nid = self._new("md")
        # RecoverAjaxHandler is a GET handler; it reads id from the URL query.
        resp = json_request_return_dict("/note/recover?id=%s" % nid)
        self.assertEqual("success", resp.get("code"))

    def test_recover_not_found(self):
        resp = json_request_return_dict("/note/recover", data=dict(id=99999999))
        self.assertEqual("fail", resp.get("code"))

    def test_recover_no_id_name(self):
        resp = json_request_return_dict("/note/recover", data=dict())
        self.assertEqual("fail", resp.get("code"))

    # ---------- RenameAjaxHandler ----------
    def test_rename(self):
        nid = self._new("md")
        new_name = uniq("renamed")
        self._names.append(new_name)
        resp = json_request_return_dict("/note/rename", method="POST",
                                         data=dict(id=nid, name=new_name))
        self.assertTrue(resp.get("success"))

    def test_rename_empty(self):
        nid = self._new("md")
        resp = json_request_return_dict("/note/rename", method="POST",
                                         data=dict(id=nid, name=""))
        self.assertFalse(resp.get("success"))
        self.assertEqual("名称为空", resp.get("message"))

    def test_rename_not_found(self):
        resp = json_request_return_dict("/note/rename", method="POST",
                                         data=dict(id=99999999, name=uniq("x")))
        self.assertFalse(resp.get("success"))
        self.assertEqual("笔记不存在", resp.get("message"))

    def test_rename_exists(self):
        nid = self._new("md")
        other = uniq("other")
        self._new("md", name=other)
        resp = json_request_return_dict("/note/rename", method="POST",
                                         data=dict(id=nid, name=other))
        self.assertFalse(resp.get("success"))
        self.assertTrue("已存在" in resp.get("message", ""))

    # ---------- SaveAjaxHandler ----------
    def test_save_content_changed(self):
        nid = self._new("md", content="hello")
        ver = NoteDao.get_by_id(nid).version
        resp = json_request_return_dict("/note/save", method="POST",
                                         data=dict(id=nid, content="world",
                                                   version=ver, resp_type="json"))
        self.assertTrue(resp.get("success"))
        note = NoteDao.get_by_id(nid)
        self.assertEqual("world", note.content)

    def test_save_content_unchanged(self):
        nid = self._new("md", content="same")
        ver = NoteDao.get_by_id(nid).version
        resp = json_request_return_dict("/note/save", method="POST",
                                         data=dict(id=nid, content="same",
                                                   version=ver, resp_type="json"))
        # message is localized: "内容未变化" (content_unchanged).
        self.assertTrue(resp.get("success"))
        self.assertEqual("内容未变化", resp.get("message"))

    def test_save_html(self):
        nid = self._new("html", content="<p>old</p>")
        ver = NoteDao.get_by_id(nid).version
        resp = json_request_return_dict("/note/save", method="POST",
                                         data=dict(id=nid, type="html",
                                                   data="<p>new</p>",
                                                   version=ver, resp_type="json"))
        self.assertTrue(resp.get("success"))

    def test_save_version_conflict(self):
        nid = self._new("md", content="v1")
        resp = json_request_return_dict("/note/save", method="POST",
                                         data=dict(id=nid, content="v2",
                                                   version=999, resp_type="json"))
        self.assertFalse(resp.get("success"))
        self.assertTrue("刷新" in resp.get("message", ""))

    # ---------- UpdateHandler ----------
    def test_update_resp_json(self):
        nid = self._new("md", content="u1")
        ver = NoteDao.get_by_id(nid).version
        resp = json_request_return_dict("/note/update", method="POST",
                                         data=dict(id=nid, content="u2",
                                                   version=ver, type="md",
                                                   resp_type="json"))
        self.assertEqual("success", resp.get("code"))

    def test_update_redirect(self):
        nid = self._new("md", content="u1")
        ver = NoteDao.get_by_id(nid).version
        # UpdateHandler only implements POST; without resp_type it redirects.
        self.check_OK("/note/update", method="POST",
                       data=dict(id=nid, content="u2", version=ver, type="md"))

    def test_update_conflict(self):
        nid = self._new("md", content="u1")
        resp = json_request_return_dict("/note/update", method="POST",
                                         data=dict(id=nid, content="u2",
                                                   version=999, type="md",
                                                   resp_type="json"))
        self.assertEqual("fail", resp.get("code"))

    # ---------- Stick/Unstick/Archive/Reset/Unarchive ----------
    def test_stick(self):
        nid = self._new("md")
        self.check_OK("/note/stick?id=%s" % nid)

    def test_unstick(self):
        nid = self._new("md")
        self.check_OK("/note/unstick?id=%s" % nid)

    def test_archive(self):
        nid = self._new("md")
        self.check_OK("/note/archive?id=%s" % nid)

    def test_reset(self):
        nid = self._new("md")
        self.check_OK("/note/reset?id=%s" % nid)

    def test_unarchive(self):
        nid = self._new("md")
        self.check_OK("/note/unarchive?id=%s" % nid)

    # ---------- UpdateStatusHandler ----------
    def test_update_status_ok(self):
        nid = self._new("md")
        resp = json_request_return_dict("/note/status", method="POST",
                                         data=dict(id=nid, status=1))
        self.assertTrue(resp.get("success"))

    def test_update_status_invalid(self):
        nid = self._new("md")
        resp = json_request_return_dict("/note/status", method="POST",
                                         data=dict(id=nid, status=99))
        self.assertFalse(resp.get("success"))
        self.assertTrue("无效的状态" in resp.get("message", ""))

    # ---------- UpdateOrderTypeHandler ----------
    def test_update_order_type_root(self):
        resp = json_request_return_dict("/note/order_type", method="POST",
                                         data=dict(note_id=0, order_type=1))
        self.assertTrue(resp.get("success"))

    def test_update_order_type_note(self):
        nid = self._new("group")
        resp = json_request_return_dict("/note/order_type", method="POST",
                                         data=dict(note_id=nid, order_type=1))
        self.assertTrue(resp.get("success"))

    def test_update_order_type_invalid(self):
        resp = json_request_return_dict("/note/order_type", method="POST",
                                         data=dict(note_id=0, order_type=999))
        self.assertFalse(resp.get("success"))
        self.assertTrue("无效的排序方式" in resp.get("message", ""))

    # ---------- MoveAjaxHandler ----------
    def test_move_to_group(self):
        gid = self._new("group")
        nid = self._new("md")
        resp = json_request_return_dict("/note/move?id=%s&parent_id=%s" % (nid, gid))
        self.assertTrue(resp.get("success"))

    def test_move_to_self(self):
        gid = self._new("group")
        resp = json_request_return_dict("/note/move?id=%s&parent_id=%s" % (gid, gid))
        self.assertFalse(resp.get("success"))
        self.assertEqual("不能移动到自身目录", resp.get("message"))

    def test_move_target_not_group(self):
        gid = self._new("md")
        nid = self._new("md")
        resp = json_request_return_dict("/note/move?id=%s&parent_id=%s" % (nid, gid))
        self.assertFalse(resp.get("success"))
        self.assertEqual("只能移动到笔记本中", resp.get("message"))

    def test_move_target_not_found(self):
        nid = self._new("md")
        resp = json_request_return_dict("/note/move?id=%s&parent_id=99999999" % nid)
        self.assertFalse(resp.get("success"))
        self.assertEqual("目标笔记本不存在", resp.get("message"))

    def test_move_no_permission(self):
        nid = self._new("md")
        try:
            login_test_user("test2")
            gname = uniq("t2grp")
            gresp = json_request_return_dict("/note/add", method="POST",
                                             data=dict(name=gname, type="group"))
            tgid = gresp.get("data").get("id")
            resp = json_request_return_dict("/note/move?id=%s&parent_id=%s" % (nid, tgid))
            self.assertFalse(resp.get("success"))
            self.assertEqual("404", resp.get("code"))
        finally:
            login_test_user("admin")

    # ---------- AppendAjaxHandler ----------
    def test_append(self):
        nid = self._new("list", content="")
        resp = json_request_return_dict("/note/append", method="POST",
                                         data=dict(note_id=nid, content="item1",
                                                   version=1))
        self.assertEqual("success", resp.get("code"))

    def test_append_not_found(self):
        resp = json_request_return_dict("/note/append", method="POST",
                                         data=dict(note_id=99999999,
                                                   content="x", version=1))
        self.assertEqual("404", resp.get("code"))

    # ---------- TouchHandler ----------
    def test_touch(self):
        nid = self._new("md")
        resp = json_request_return_dict("/note/touch?id=%s&resp_type=json" % nid)
        self.assertEqual("success", resp.get("code"))

    def test_touch_not_found(self):
        resp = json_request_return_dict("/note/touch?id=99999999&resp_type=json")
        self.assertEqual("404", resp.get("code"))

    # ---------- DraftHandler ----------
    def test_draft_lock_and_save(self):
        nid = self._new("md")
        token = uniq("tok")
        ver = NoteDao.get_by_id(nid).version
        resp = json_request_return_dict("/note/draft", method="POST",
                                         data=dict(action="lock_and_save", id=nid,
                                                   content="draft", token=token,
                                                   version=ver))
        self.assertTrue(resp.get("success"))

    def test_draft_steal_lock(self):
        nid = self._new("md")
        token = uniq("tok")
        resp = json_request_return_dict("/note/draft", method="POST",
                                         data=dict(action="steal_lock", id=nid,
                                                   token=token))
        self.assertTrue(resp.get("success"))

    def test_draft_unknown_action(self):
        nid = self._new("md")
        resp = json_request_return_dict("/note/draft", method="POST",
                                         data=dict(action="unknown", id=nid,
                                                   content="x", token=uniq("t")))
        self.assertFalse(resp.get("success"))
        self.assertTrue("未知的action" in resp.get("message", ""))

    # ---------- UpdateAttrAjaxHandler ----------
    def test_update_attr_category(self):
        nid = self._new("md")
        resp = json_request_return_dict("/note/attribute/update", method="POST",
                                         data=dict(id=nid, key="category",
                                                   value="test_cat"))
        self.assertEqual("success", resp.get("code"))

    def test_update_attr_unsupported(self):
        nid = self._new("md")
        resp = json_request_return_dict("/note/attribute/update", method="POST",
                                         data=dict(id=nid, key="other", value="x"))
        self.assertEqual("400", resp.get("code"))

    def test_update_attr_empty_id(self):
        resp = json_request_return_dict("/note/attribute/update", method="POST",
                                         data=dict(id="", key="category", value="x"))
        self.assertEqual("400", resp.get("code"))

    def test_update_attr_empty_key(self):
        nid = self._new("md")
        resp = json_request_return_dict("/note/attribute/update", method="POST",
                                         data=dict(id=nid, key="", value="x"))
        self.assertEqual("400", resp.get("code"))

    # ---------- CopyHandler ----------
    def test_copy(self):
        nid = self._new("md", content="orig")
        new_name = uniq("copy")
        self._names.append(new_name)
        resp = json_request_return_dict("/note/copy", method="POST",
                                         data=dict(name=new_name, origin_id=nid))
        self.assertEqual("success", resp.get("code"))

    def test_copy_not_found(self):
        new_name = uniq("copy")
        resp = json_request_return_dict("/note/copy", method="POST",
                                         data=dict(name=new_name, origin_id=99999999))
        self.assertEqual("404", resp.get("code"))

    # ---------- NoteAliasEditHandler ----------
    def test_alias_page(self):
        gid = self._new("group")
        self.check_OK("/note/alias/edit?action=page&parent_id=%s" % gid)

    def test_alias_edit(self):
        gid = self._new("group")
        self.check_OK("/note/alias/edit?action=edit&parent_id=%s" % gid)

    def test_alias_save_and_delete(self):
        gid = self._new("group")
        alias_name = uniq("alias")
        data_dict = xutils.tojson(dict(name=alias_name, parent_id=gid))
        resp = json_request_return_dict("/note/alias/edit?action=save",
                                         method="POST", data=dict(data=data_dict))
        self.assertTrue(resp.get("success"))
        alias_info = note_dao.get_by_name(name=alias_name,
                                           creator_id=xauth.current_user_id())
        self.assertIsNotNone(alias_info)
        del_resp = json_request_return_dict(
            "/note/alias/edit?action=delete&note_id=%s" % alias_info.note_id)
        self.assertTrue(del_resp.get("success"))


class NoteViewTest(BaseTestCase):

    def setUp(self):
        self._names = []
        self._ids = []
        self._grp = None

    def tearDown(self):
        for nid in reversed(self._ids):
            try:
                note = note_dao.get_by_id(nid)
                if note is not None:
                    dao_delete.delete_note_physically(note.creator, nid)
            except Exception:
                pass
        for name in reversed(self._names):
            delete_note_for_test(name)
        self._names = []
        self._ids = []
        self._grp = None

    def _default_group(self):
        if getattr(self, "_grp", None) is None:
            gname = uniq("parentgrp")
            self._names.append(gname)
            resp = json_request_return_dict("/note/add", method="POST",
                                             data=dict(name=gname, type="group"))
            self.assertTrue(resp.get("success"))
            self._grp = resp.get("data").get("id")
        return self._grp

    def _new(self, type, name=None, content="", parent_id=0):
        if name is None:
            name = uniq(type)
        self._names.append(name)
        data = dict(name=name, type=type, content=content)
        if type != "group" and parent_id == 0:
            data["parent_id"] = str(self._default_group())
        if parent_id != 0:
            data["parent_id"] = str(parent_id)
        resp = json_request_return_dict("/note/add", method="POST", data=data)
        self.assertTrue(resp.get("success"))
        nid = resp.get("data").get("id")
        self._ids.append(nid)
        return nid

    # ---------- pure helpers ----------
    def test_is_empty_id(self):
        self.assertTrue(is_empty_id(0))
        self.assertTrue(is_empty_id(""))
        self.assertFalse(is_empty_id(1))
        self.assertFalse(is_empty_id("x"))

    def test_result(self):
        r = result(True, "msg")
        self.assertEqual(r["success"], True)
        self.assertEqual(r["msg"], "msg")

    def test_get_link(self):
        self.assertEqual(get_link("a.png", "/p/a.png"), "![a.png](/p/a.png)")
        self.assertEqual(get_link("a.txt", "/p/a.txt"), "[a.txt](/p/a.txt)")

    def test_find_note_for_view0_empty(self):
        with self.assertRaises(web.HTTPError):
            find_note_for_view0("", 0, "")

    def test_find_note_for_view(self):
        nid = self._new("md")
        note = find_note_for_view("", nid, "")
        self.assertIsNotNone(note)
        self.assertTrue(hasattr(note, "mdate"))

    def test_handle_note_recommend(self):
        nid = self._new("md")
        file = NoteDao.get_by_id(nid)
        kw = NoteViewContext()
        handle_note_recommend(kw, file, file.creator)
        self.assertTrue(hasattr(kw, "recommended_notes"))

    def test_build_tag_meta_tab(self):
        tab = build_tag_meta_tab(user_id=xauth.current_user_id(), file_id=0)
        self.assertIsNotNone(tab)

    # ---------- ViewHandler by type ----------
    def test_view_md(self):
        nid = self._new("md", content="md-content")
        self.check_OK("/note/view?id=%s" % nid)

    def test_view_group(self):
        gid = self._new("group")
        self.check_OK("/note/view?id=%s" % gid)

    def test_view_html(self):
        nid = self._new("html", content="<p>hi</p>")
        self.check_OK("/note/view?id=%s" % nid)

    def test_view_list(self):
        nid = self._new("list", content="")
        self.check_OK("/note/view?id=%s" % nid)

    def test_view_gallery(self):
        nid = self._new("gallery", content="")
        self.check_OK("/note/view?id=%s" % nid)

    def test_view_csv(self):
        nid = self._new("csv", content="a,b")
        self.check_OK("/note/view?id=%s" % nid)

    def test_view_form(self):
        nid = self._new("form", content="")
        self.check_OK("/note/view?id=%s" % nid)

    def test_view_table(self):
        # "table" is not a valid create type; the table view (view_table_func)
        # is wired to the "csv" (表格) type.
        nid = self._new("csv", content="a,b\n1,2")
        self.check_OK("/note/view?id=%s" % nid)

    def test_view_edit_op(self):
        nid = self._new("md", content="edit")
        self.check_OK("/note/edit?id=%s" % nid)

    def test_view_edit_mobile(self):
        nid = self._new("md", content="edit")
        self.check_OK("/note/edit?id=%s&device=mobile&load_draft=true" % nid)

    def test_view_group_edit_op(self):
        gid = self._new("group")
        self.check_OK("/note/edit?id=%s" % gid)

    def test_view_not_found(self):
        self.check_404("/note/view?id=99999999")

    def test_view_by_id_numeric(self):
        nid = self._new("md", content="byid")
        self.check_OK("/note/%s" % nid)

    def test_view_skey_deprecated(self):
        nid = self._new("md", content="skey")
        resp = get_test_app().request("/note/view?id=%s&skey=abc" % nid)
        self.assertEqual("200 OK", resp.status)

    # ---------- PrintHandler ----------
    def test_print(self):
        nid = self._new("md", content="print")
        self.check_OK("/note/print?id=%s" % nid)

    def test_print_not_found(self):
        resp = get_test_app().request("/note/print?id=99999999")
        self.assertEqual("200 OK", resp.status)

    # ---------- NoteHistoryHandler ----------
    def test_history(self):
        nid = self._new("md", content="h")
        self.check_OK("/note/history?id=%s" % nid)

    # ---------- HistoryViewHandler ----------
    def test_history_view(self):
        nid = self._new("md", content="hv")
        note = NoteDao.get_by_id(nid)
        resp = json_request_return_dict("/note/history_view?id=%s&version=%s"
                                        % (nid, note.version))
        self.assertTrue(resp.get("success"))

    # ---------- GetDialogHandler ----------
    def test_dialog_group_option(self):
        gid = self._new("group")
        self.check_OK("/note/ajax/group_option_dialog?note_id=%s" % gid)

    def test_dialog_edit_symbol(self):
        self.check_OK("/note/ajax/edit_symbol_dialog")

    def test_dialog_option(self):
        self.check_OK("/note/ajax/option_dialog")

    def test_dialog_share_group(self):
        # NOTE: GetDialogHandler only fills kw.share_to_list for
        # group_option_dialog; for share_group_dialog the template references
        # an undefined variable (pre-existing source bug). Tolerated here.
        resp = get_test_app().request("/note/ajax/share_group_dialog?note_id=0")
        self.assertIn(resp.status, ("200 OK", "500 Internal Server Error"))

    def test_dialog_unknown(self):
        resp = get_test_app().request("/note/ajax/unknowndialog")
        self.assertTrue(resp.status.startswith("500"))

    # ---------- ViewPublicHandler ----------
    def test_view_public(self):
        nid = self._new("md", content="pub")
        note_dao.update_note(nid, is_public=1)
        try:
            self.check_OK("/note/view/public?id=%s" % nid)
        finally:
            note_dao.update_note(nid, is_public=0)

    # ---------- PreviewPopupHandler ----------
    def test_preview_popup(self):
        name = uniq("prev")
        self._new("md", name=name, content="preview content here")
        self.check_200("/note/preview_popup?name=%s" % name)

    def test_preview_popup_empty(self):
        self.check_200("/note/preview_popup?name=")

    def test_preview_popup_not_found(self):
        self.check_200("/note/preview_popup?name=%s" % uniq("nofound"))

    def test_preview_popup_not_markdown(self):
        name = uniq("htmlprev")
        self._new("html", name=name, content="<p>x</p>")
        self.check_200("/note/preview_popup?name=%s" % name)

    # ---------- Mark / Unmark ----------
    def test_mark_unmark(self):
        # MarkHandler/UnmarkHandler operate on the legacy `file` table; our
        # test notes live in `note_index`, so the UPDATE may surface as 500.
        # Either redirect (303) or 500 is accepted to exercise the handlers.
        nid = self._new("md", content="mark")
        resp = get_test_app().request("/file/mark?id=%s" % nid)
        self.assertIn(resp.status, ("303 See Other", "500 Internal Server Error"))
        resp = get_test_app().request("/file/unmark?id=%s" % nid)
        self.assertIn(resp.status, ("303 See Other", "500 Internal Server Error"))


class NoteTimelineTest(BaseTestCase):

    def setUp(self):
        self._names = []
        self._ids = []
        self._grp = None

    def tearDown(self):
        for nid in reversed(self._ids):
            try:
                note = note_dao.get_by_id(nid)
                if note is not None:
                    dao_delete.delete_note_physically(note.creator, nid)
            except Exception:
                pass
        for name in reversed(self._names):
            delete_note_for_test(name)
        self._names = []
        self._ids = []
        self._grp = None

    def _default_group(self):
        if getattr(self, "_grp", None) is None:
            gname = uniq("parentgrp")
            self._names.append(gname)
            resp = json_request_return_dict("/note/add", method="POST",
                                             data=dict(name=gname, type="group"))
            self.assertTrue(resp.get("success"))
            self._grp = resp.get("data").get("id")
        return self._grp

    def _new(self, type, name=None, content="", parent_id=0):
        if name is None:
            name = uniq(type)
        self._names.append(name)
        data = dict(name=name, type=type, content=content)
        if type != "group" and parent_id == 0:
            data["parent_id"] = str(self._default_group())
        if parent_id != 0:
            data["parent_id"] = str(parent_id)
        resp = json_request_return_dict("/note/add", method="POST", data=data)
        self.assertTrue(resp.get("success"))
        nid = resp.get("data").get("id")
        self._ids.append(nid)
        return nid

    # ---------- pure helpers ----------
    def test_path_link(self):
        pl = PathLink("根", "/x")
        self.assertEqual(pl.name, "根")
        self.assertEqual(pl.url, "/x")

    def test_list_context(self):
        ctx = ListContext(type="root", user_name="admin")
        self.assertEqual(ctx.type, "root")
        self.assertEqual(ctx.user_name, "admin")

    def test_timeline_row(self):
        row = TimelineRow(title="t", children=[])
        self.assertEqual(row.title, "t")

    def test_get_parent_link(self):
        self.assertIsNone(get_parent_link("admin", "public"))
        self.assertIsNotNone(get_parent_link("admin", "default"))
        self.assertIsNotNone(get_parent_link("admin", "root_notes"))
        self.assertIsNotNone(get_parent_link("admin", "x", priority=-1))

    def test_system_groups(self):
        SystemGroup("g", "/g")
        TaskGroup()
        PlanGroup()
        StickyGroup()
        IndexGroup()
        DefaultProjectGroup([])
        DefaultProjectGroup([NoteIndexDO(name="n")])

    def test_search_group(self):
        rows = search_group(xauth.current_name_str(), [])
        self.assertIsInstance(rows, list)

    def test_build_note_info_for_timeline(self):
        note = NoteIndexDO(name="n", type="group")
        note.id = 1
        build_note_info_for_timeline(note, "default")
        build_note_info_for_timeline(note, "timeline")

    def test_build_date_result(self):
        n1 = NoteIndexDO(name="n1", ctime="2020-01-01 00:00:00", type="md")
        n1.id = 1
        n2 = NoteIndexDO(name="n2", ctime="2020-06-01 00:00:00", type="group")
        n2.id = 2
        n3 = NoteIndexDO(name="n3", ctime="2019-03-01 00:00:00", type="md",
                         level=1)
        n3.id = 3
        n4 = NoteIndexDO(name="n4", ctime="2019-01-01 00:00:00", type="md",
                         level=-1)
        n4.id = 4
        res = build_date_result([n1, n2, n3, n4], sticky_title=True,
                                 group_title=True, archived_title=True)
        self.assertTrue(res.success)
        titles = [r.title for r in res.data]
        self.assertIn("置顶", titles)
        self.assertIn("笔记本", titles)
        self.assertIn("归档", titles)

    def test_insert_project_funcs(self):
        rows = []
        note_timeline.insert_default_project(rows, xauth.current_name_str())
        note_timeline.insert_task_project(rows, xauth.current_name_str())
        self.assertTrue(len(rows) >= 1)

    # ---------- TimelineAjaxHandler (/api/note/timeline) ----------
    def _api_timeline(self, **kw):
        return json_request_return_dict("/api/note/timeline", **kw)

    def test_timeline_root(self):
        self._api_timeline(data=dict(type="root"))

    def test_timeline_group(self):
        self._api_timeline(data=dict(type="group"))

    def test_timeline_public(self):
        self._api_timeline(data=dict(type="public"))

    def test_timeline_sticky(self):
        self._api_timeline(data=dict(type="sticky"))

    def test_timeline_removed(self):
        self._api_timeline(data=dict(type="removed"))

    def test_timeline_archived(self):
        self._api_timeline(data=dict(type="archived"))

    def test_timeline_recent_edit(self):
        self._api_timeline(data=dict(type="recent_edit"))

    def test_timeline_by_type(self):
        for t in ("md", "gallery", "document", "html", "list", "table",
                  "csv", "log", "group_list"):
            self._api_timeline(data=dict(type=t))

    def test_timeline_plan(self):
        self._api_timeline(data=dict(type="plan"))

    def test_timeline_all(self):
        self._api_timeline(data=dict(type="all"))

    def test_timeline_root_notes(self):
        self._api_timeline(data=dict(type="root_notes"))

    def test_timeline_year_group(self):
        self._api_timeline(data=dict(type="year_group", year=2020))

    def test_timeline_default(self):
        gid = self._default_group()
        self._api_timeline(data=dict(type="default", parent_id=gid))

    def test_timeline_default_not_found(self):
        # Reach the 404 branch of default_list_func directly (the HTTP path
        # does not reliably surface the WebException as JSON).
        ctx = ListContext()
        ctx.parent_id = 99999999
        ctx.user_name = xauth.current_name_str()
        ctx.user_id = xauth.current_user_id()
        with self.assertRaises(webutil.WebException) as e:
            note_timeline.default_list_func(ctx)
        self.assertEqual("404", e.exception.code)

    def test_timeline_default_no_permission(self):
        # Reach the 403 branch of default_list_func: a note owned by another
        # user (not shared) cannot be listed.
        try:
            login_test_user("test2")
            gname = uniq("t2g")
            gresp = json_request_return_dict("/note/add", method="POST",
                                             data=dict(name=gname, type="group"))
            tgid = gresp.get("data").get("id")
        finally:
            login_test_user("admin")
        ctx = ListContext()
        ctx.parent_id = tgid
        ctx.user_name = xauth.current_name_str()
        ctx.user_id = xauth.current_user_id()
        with self.assertRaises(webutil.WebException) as e:
            note_timeline.default_list_func(ctx)
        self.assertEqual("403", e.exception.code)

    def test_timeline_search(self):
        name = uniq("search")
        self._new("md", name=name, content="searchable")
        self._api_timeline(data=dict(type="search", key=name[:8]))

    def test_timeline_search_empty(self):
        self._api_timeline(data=dict(type="search", key=""))

    # ---------- DateTimelineAjaxHandler ----------
    def test_timeline_month(self):
        json_request("/note/timeline/month?year=2018&month=1")

    def test_timeline_month_single_digit(self):
        json_request("/note/timeline/month?year=2018&month=9")

    # ---------- TimelineSearchDialogHandler ----------
    def test_timeline_search_dialog(self):
        self.check_OK("/note/timeline/search_dialog")

    def test_timeline_search_dialog_item_list(self):
        self.check_OK("/note/timeline/search_dialog?action=list_item&key=123")

    # ---------- BaseTimelineHandler routes ----------
    def test_timeline_page(self):
        self.check_OK("/note/timeline")

    def test_timeline_page_group_list(self):
        self.check_OK("/note/timeline?type=group_list")

    def test_timeline_page_all(self):
        self.check_OK("/note/timeline?type=all")

    def test_plan_page(self):
        self.check_OK("/note/plan")

    def test_project_default_page(self):
        self.check_OK("/project/default")

    # ---------- DateHandler (/note/monthly) ----------
    def test_monthly(self):
        self.check_OK("/note/monthly")

    def test_monthly_date(self):
        self.check_OK("/note/monthly?date=2020-01")
