# -*- coding:utf-8 -*-
# Coverage tests for note_tag / note_meta / note_calendar / note_share
# Run ONLY this file (see task instructions).

import uuid
import json as _json

try:
    import test_base
    from test_base import BaseTestCase, json_request, json_request_return_dict, get_test_app, login_test_user, logout_test_user
except ImportError:
    from tests import test_base
    from tests.test_base import BaseTestCase, json_request, json_request_return_dict, get_test_app, login_test_user, logout_test_user

from xnote.core import xauth
from xutils import Storage

from xnote_handlers.note import dao as note_dao
from xnote_handlers.note import dao_tag
from xnote_handlers.note import dao_share
from xnote_handlers.note.dao import NoteIndexDao, get_by_id
from xnote_handlers.note.dao_tag import NoteTagInfoDao, NoteTagBindDao
from xnote_handlers.note.dao_meta import NoteMetaDao
from xnote_handlers.note.models import NoteViewContext, NoteIndexDO, NoteMetaRecord
from xnote_handlers.note.note_meta import NoteMetaService, NoteMetaHandler
from xnote_handlers.note.note_calendar import NoteCalendarHandler, CalendarCell, CalendarRow, HOLIDAY_MAP
from xnote.plugin import DataTable, TabBox

from tests.test_base_note import delete_note_for_test, create_note_for_test, get_default_group_id


class _CovBase(BaseTestCase):
    """Common helpers + cleanup for the coverage test file."""

    def setUp(self):
        super().setUp()
        self.created_names = []
        login_test_user("admin")

    def tearDown(self):
        for name in self.created_names:
            try:
                delete_note_for_test(name)
            except Exception:
                pass
        super().tearDown()

    def uniq(self, prefix):
        name = "%s_%s" % (prefix, uuid.uuid4().hex[:12])
        self.created_names.append(name)
        return name

    def _new_note(self, prefix, type="md", content="", parent_id=0, tags=""):
        name = self.uniq(prefix)
        return create_note_for_test(type=type, name=name, content=content, parent_id=parent_id, tags=tags)

    def _get_note_obj(self, note_id):
        return NoteIndexDao.get_by_id(note_id)


class TestNoteTag(_CovBase):

    # ---------------- handler coverage ----------------

    def test_tag_update_empty(self):
        note_id = self._new_note("tag_upd_empty")
        # empty tags -> bind empty list
        resp = json_request_return_dict("/note/tag/update", method="POST",
                                        data=dict(file_id=note_id, tags=""))
        self.assertTrue(resp.get_bool("success"))

    def test_tag_update_with_tags(self):
        note_id = self._new_note("tag_upd")
        resp = json_request_return_dict("/note/tag/update", method="POST",
                                        data=dict(file_id=note_id, tags="tagA tagB"))
        self.assertTrue(resp.get_bool("success"))
        info = note_dao.get_by_id(note_id)
        self.assertIn("taga", [t.lower() for t in info.tags])

    def test_tag_update_get_alias(self):
        # GET delegates to POST
        note_id = self._new_note("tag_upd_get")
        resp = json_request_return_dict("/note/tag/update?file_id=%s&tags=tagC" % note_id)
        self.assertTrue(resp.get_bool("success"))

    def test_tag_info(self):
        note_id = self._new_note("tag_info", tags="InfoTagX")
        self.check_200("/note/taginfo?tag_code=infotagx")

    def test_tag_list_page(self):
        self.check_200("/note/taglist")
        self.check_200("/note/taglist?tag_type=1")
        self.check_200("/note/taglist?tag_type=2")

    def test_create_tag_empty_name(self):
        group_id = self._new_note("tag_create_grp", type="group")
        resp = json_request_return_dict("/note/tag/create", method="POST",
                                        data=dict(tag_type="group", tag_name="", group_id=group_id))
        self.assertFalse(resp.get_bool("success"))

    def test_create_tag_note_no_group(self):
        resp = json_request_return_dict("/note/tag/create", method="POST",
                                        data=dict(tag_type="note", tag_name="X"))
        self.assertFalse(resp.get_bool("success"))

    def test_create_tag_invalid_type(self):
        resp = json_request_return_dict("/note/tag/create", method="POST",
                                        data=dict(tag_type="invalid", tag_name="X"))
        self.assertFalse(resp.get_bool("success"))

    def test_create_tag_group_success(self):
        group_id = self._new_note("tag_create_ok", type="group")
        resp = json_request_return_dict("/note/tag/create", method="POST",
                                        data=dict(tag_type="group", tag_name="NewTag1", group_id=group_id))
        self.assertTrue(resp.get_bool("success"))

    def test_create_tag_group_duplicate(self):
        group_id = self._new_note("tag_create_dup", type="group")
        json_request_return_dict("/note/tag/create", method="POST",
                                 data=dict(tag_type="group", tag_name="DupTag", group_id=group_id))
        resp = json_request_return_dict("/note/tag/create", method="POST",
                                        data=dict(tag_type="group", tag_name="DupTag", group_id=group_id))
        self.assertFalse(resp.get_bool("success"))

    def test_create_tag_note_success(self):
        group_id = self._new_note("tag_create_note", type="group")
        resp = json_request_return_dict("/note/tag/create", method="POST",
                                        data=dict(tag_type="note", tag_name="NoteTag1", group_id=group_id))
        self.assertTrue(resp.get_bool("success"))

    def test_delete_tag_empty_list(self):
        group_id = self._new_note("tag_del_empty", type="group")
        resp = json_request_return_dict("/note/tag/delete", method="POST",
                                        data=dict(tag_type="group", group_id=group_id, tag_code_list="[]"))
        self.assertFalse(resp.get_bool("success"))

    def test_delete_tag_success(self):
        group_id = self._new_note("tag_del_ok", type="group")
        json_request_return_dict("/note/tag/create", method="POST",
                                 data=dict(tag_type="group", tag_name="DelTag", group_id=group_id))
        resp = json_request_return_dict("/note/tag/delete", method="POST",
                                        data=dict(tag_type="group", group_id=group_id,
                                                  tag_code_list=_json.dumps(["DelTag"])))
        self.assertTrue(resp.get_bool("success"))

    def test_delete_tag_invalid_type(self):
        resp = json_request_return_dict("/note/tag/delete", method="POST",
                                        data=dict(tag_type="invalid", group_id=0, tag_code_list="[]"))
        self.assertFalse(resp.get_bool("success"))

    def test_tag_list_ajax_group(self):
        resp = json_request_return_dict("/note/tag/list?tag_type=group")
        self.assertTrue(resp.get_bool("success"))
        # resp["data"] is the plain dict; resp.get_dict("data") is a
        # TypedDict whose `__getitem__` breaks `assertIn`
        self.assertIn("all_list", resp["data"])

    def test_tag_list_ajax_note(self):
        group_id = self._new_note("tag_list_note", type="group")
        resp = json_request_return_dict("/note/tag/list?tag_type=note&group_id=%s" % group_id)
        self.assertTrue(resp.get_bool("success"))

    def test_tag_list_ajax_invalid(self):
        resp = json_request_return_dict("/note/tag/list?tag_type=unknown")
        self.assertFalse(resp.get_bool("success"))

    def test_bind_tag_group(self):
        group_id = self._new_note("tag_bind_grp", type="group")
        resp = json_request_return_dict("/note/tag/bind", method="POST",
                                        data=dict(tag_type="group", group_id=group_id,
                                                  tag_names=_json.dumps(["b1"])))
        self.assertTrue(resp.get_bool("success"))

    def test_bind_tag_group_not_exist(self):
        resp = json_request_return_dict("/note/tag/bind", method="POST",
                                        data=dict(tag_type="group", group_id=999999999,
                                                  tag_names=_json.dumps(["b1"])))
        self.assertFalse(resp.get_bool("success"))

    def test_bind_tag_note(self):
        note_id = self._new_note("tag_bind_note")
        resp = json_request_return_dict("/note/tag/bind", method="POST",
                                        data=dict(tag_type="note", note_id=note_id,
                                                  tag_names=_json.dumps(["b2"])))
        self.assertTrue(resp.get_bool("success"))

    def test_bind_tag_invalid(self):
        resp = json_request_return_dict("/note/tag/bind", method="POST",
                                        data=dict(tag_type="invalid"))
        self.assertFalse(resp.get_bool("success"))

    def test_add_note_to_tag_empty_code(self):
        resp = json_request_return_dict("/note/tag/add_note_to_tag", method="POST",
                                        data=dict(tag_code="", note_ids="1"))
        self.assertFalse(resp.get_bool("success"))

    def test_add_note_to_tag_success(self):
        note_id = self._new_note("tag_addnote")
        resp = json_request_return_dict("/note/tag/add_note_to_tag", method="POST",
                                        data=dict(tag_code="addtagx", note_ids=str(note_id)))
        self.assertTrue(resp.get_bool("success"))

    def test_suggest_tag(self):
        group_id = self._new_note("tag_suggest", type="group")
        resp = json_request_return_dict("/note/tag/suggest?group_id=%s" % group_id)
        self.assertTrue(resp.get_bool("success"))

    def test_tag_list_html(self):
        group_id = self._new_note("tag_list_html", type="group")
        self.check_200("/note/tag/list_html?group_id=%s" % group_id)

    def test_tag_bind_dialog_valid(self):
        group_id = self._new_note("tag_dialog", type="group")
        self.check_200("/note/tag/bind_dialog?group_id=%s&tags_json=%s"
                       % (group_id, _json.dumps(["a"])))

    def test_tag_bind_dialog_invalid_type(self):
        app = get_test_app()
        resp = app.request("/note/tag/bind_dialog?group_id=0&tags_json=%s"
                           % _json.dumps({"x": 1}), method="GET")
        self.assertIn("无效的类型", resp.data.decode("utf-8"))

    # ---------------- direct helper coverage ----------------

    def test_helper_bind_tags(self):
        note_id = self._new_note("helper_bind")
        user_id = xauth.current_user_id()
        dao_tag.bind_tags(user_id=user_id, note_id=note_id, tags=["h1", "h2"])
        info = note_dao.get_by_id(note_id)
        self.assertTrue(len(info.tags) >= 2)

    def test_helper_batch_get_tags_empty(self):
        self.assertIsNone(dao_tag.batch_get_tags_by_notes([]))

    def test_helper_get_name_by_code(self):
        # unknown / empty code is echoed back (not a system tag)
        self.assertEqual(dao_tag.get_name_by_code(""), "")
        self.assertEqual(dao_tag.get_name_by_code("system"), "system")
        # a known system tag code returns its display name
        self.assertEqual(dao_tag.get_name_by_code("_todo"), "待办")

    def test_helper_handle_tag_for_note(self):
        note_id = self._new_note("helper_handle")
        note = self._get_note_obj(note_id)
        note.tags = ["x", "y"]
        dao_tag.handle_tag_for_note(note)
        self.assertTrue(len(note.tag_info_list) == 2)

    def test_helper_append_tag(self):
        note_id = self._new_note("helper_append")
        dao_tag.append_tag(note_id, "appended")
        info = note_dao.get_by_id(note_id)
        self.assertIn("appended", info.tags)

    def test_helper_get_skip_tag_type(self):
        self.assertTrue(dao_tag.get_skip_tag_type(0))
        self.assertFalse(dao_tag.get_skip_tag_type(1))

    def test_helper_list_tag_category_detail(self):
        user_id = xauth.current_user_id()
        result = dao_tag.list_tag_category_detail(user_id=user_id, tag_type=1)
        self.assertTrue(isinstance(result, list))
        result2 = dao_tag.list_tag_category_detail(user_id=user_id, tag_type=2)
        self.assertTrue(isinstance(result2, list))


class TestNoteMeta(_CovBase):

    # ---------------- handler coverage ----------------

    def test_meta_save_invalid_note_id(self):
        data = _json.dumps(dict(note_id=0, meta_key="mobile", meta_value="1"))
        resp = json_request_return_dict("/note/meta?action=save", method="POST", data=dict(data=data))
        self.assertFalse(resp.get_bool("success"))

    def test_meta_save_meta_id_not_found(self):
        note_id = self._new_note("meta_save_nf")
        data = _json.dumps(dict(meta_id=999999999, meta_key="mobile", meta_value="1", note_id=note_id))
        resp = json_request_return_dict("/note/meta?action=save", method="POST", data=dict(data=data))
        self.assertFalse(resp.get_bool("success"))

    def test_meta_save_new_custom_empty_name(self):
        note_id = self._new_note("meta_newcustom")
        data = _json.dumps(dict(meta_key="_new_custom", meta_name="", note_id=note_id))
        resp = json_request_return_dict("/note/meta?action=save", method="POST", data=dict(data=data))
        self.assertFalse(resp.get_bool("success"))

    def test_meta_save_duplicate(self):
        note_id = self._new_note("meta_dup")
        data1 = _json.dumps(dict(meta_key="mobile", meta_value="123", note_id=note_id))
        r1 = json_request_return_dict("/note/meta?action=save", method="POST", data=dict(data=data1))
        self.assertTrue(r1.get_bool("success"))
        data2 = _json.dumps(dict(meta_key="mobile", meta_value="456", note_id=note_id))
        r2 = json_request_return_dict("/note/meta?action=save", method="POST", data=dict(data=data2))
        self.assertFalse(r2.get_bool("success"))

    def test_meta_save_note_field(self):
        note_id = self._new_note("meta_field")
        data = _json.dumps(dict(meta_key="_manual_short_desc", meta_value="hello", note_id=note_id))
        resp = json_request_return_dict("/note/meta?action=save", method="POST", data=dict(data=data))
        self.assertTrue(resp.get_bool("success"))
        info = note_dao.get_by_id(note_id)
        self.assertEqual(info.manual_short_desc, "hello")

    def test_meta_save_custom(self):
        note_id = self._new_note("meta_custom")
        data = _json.dumps(dict(meta_key="custom_x", meta_value="v", note_id=note_id))
        resp = json_request_return_dict("/note/meta?action=save", method="POST", data=dict(data=data))
        self.assertTrue(resp.get_bool("success"))

    def test_meta_edit_branches(self):
        note_id = self._new_note("meta_edit")
        # select branch
        self.check_200("/note/meta?action=edit&meta_id=0&meta_key=_type&note_id=%s" % note_id)
        # date branch
        self.check_200("/note/meta?action=edit&meta_id=0&meta_key=_create_date&note_id=%s" % note_id)
        # number branch
        self.check_200("/note/meta?action=edit&meta_id=0&meta_key=birth_year&note_id=%s" % note_id)
        # text / else branch
        self.check_200("/note/meta?action=edit&meta_id=0&meta_key=mobile&note_id=%s" % note_id)
        # new custom readonly branch
        self.check_200("/note/meta?action=edit&meta_id=0&meta_key=_new_custom&note_id=%s" % note_id)

    def test_meta_edit_meta_id_not_found(self):
        note_id = self._new_note("meta_edit_nf")
        resp = json_request_return_dict(
            "/note/meta?action=edit&meta_id=999999999&meta_key=mobile&note_id=%s" % note_id)
        self.assertFalse(resp.get_bool("success"))

    def test_meta_edit_meta_id_found(self):
        note_id = self._new_note("meta_edit_found")
        data = _json.dumps(dict(meta_key="mobile", meta_value="555", note_id=note_id))
        json_request_return_dict("/note/meta?action=save", method="POST", data=dict(data=data))
        record = NoteMetaDao.get_by_meta_key(note_id=note_id, meta_key="mobile")
        self.assertIsNotNone(record)
        self.check_200("/note/meta?action=edit&meta_id=%s&meta_key=mobile&note_id=%s"
                       % (record.meta_id, note_id))

    def test_meta_delete_not_found(self):
        resp = json_request_return_dict("/note/meta?action=delete&meta_id=999999999")
        self.assertFalse(resp.get_bool("success"))

    def test_meta_delete_success(self):
        note_id = self._new_note("meta_delete")
        data = _json.dumps(dict(meta_key="mobile", meta_value="999", note_id=note_id))
        json_request_return_dict("/note/meta?action=save", method="POST", data=dict(data=data))
        record = NoteMetaDao.get_by_meta_key(note_id=note_id, meta_key="mobile")
        resp = json_request_return_dict("/note/meta?action=delete&meta_id=%s" % record.meta_id)
        self.assertTrue(resp.get_bool("success"))

    def test_meta_view_render(self):
        note_id = self._new_note("meta_view")
        # tab != meta -> get_meta_list branch
        self.check_200("/note/view/%s" % note_id)
        # meta_category all -> _render_all
        self.check_200("/note/view/%s?tab=meta&meta_category=all" % note_id)
        # meta_category basic -> _render_category (basic)
        self.check_200("/note/view/%s?tab=meta&meta_category=basic" % note_id)
        # meta_category people -> _render_category (people)
        self.check_200("/note/view/%s?tab=meta&meta_category=people" % note_id)
        # meta_category custom -> _render_category (custom)
        self.check_200("/note/view/%s?tab=meta&meta_category=custom" % note_id)

    # ---------------- direct helper coverage ----------------

    def test_service_find_meta(self):
        r1 = NoteMetaRecord()
        r1.meta_key = "k1"
        r2 = NoteMetaRecord()
        r2.meta_key = "k2"
        self.assertIs(NoteMetaService.find_meta([r1, r2], "k2"), r2)
        self.assertIsNone(NoteMetaService.find_meta([r1, r2], "kx"))

    def test_service_get_meta_list_no_info(self):
        note_id = self._new_note("meta_svc_list")
        records = NoteMetaService.get_meta_list(note_id=note_id, note_info=None)
        self.assertTrue(isinstance(records, list))
        for r in records:
            self.assertTrue(hasattr(r, "meta_name"))

    def test_service_get_meta_list_with_info(self):
        note_id = self._new_note("meta_svc_info")
        note = self._get_note_obj(note_id)
        records = NoteMetaService.get_meta_list(note_id=note_id, note_info=note, view_tab="all")
        self.assertTrue(isinstance(records, list))
        self.assertTrue(len(records) >= 1)

    def test_service_fill_links(self):
        row0 = NoteMetaRecord()
        row0.note_id = 5
        row0.meta_id = 0
        row0.meta_name = "n"
        row0.meta_value = "v"
        NoteMetaService._fill_links(row0)
        self.assertIn("note_id=5", row0.edit_url)

        row1 = NoteMetaRecord()
        row1.note_id = 5
        row1.meta_id = 7
        row1.meta_name = "n"
        NoteMetaService._fill_links(row1)
        self.assertIn("meta_id=7", row1.delete_url)

    def test_service_render_all_and_category(self):
        note_id = self._new_note("meta_svc_render")
        note = self._get_note_obj(note_id)
        ctx = NoteViewContext()
        ctx.file = note
        ctx.note_id = note_id

        table = DataTable()
        NoteMetaService._render_all(ctx, table)
        self.assertTrue(len(table.rows) > 0)

        table2 = DataTable()
        NoteMetaService._render_category(ctx, table2, "basic")
        self.assertTrue(len(table2.rows) > 0)

    def test_service_render_view_ctx_non_meta(self):
        note_id = self._new_note("meta_svc_ctx")
        note = self._get_note_obj(note_id)
        ctx = NoteViewContext()
        ctx.tab = "content"
        ctx.file = note
        ctx.note_id = note_id
        NoteMetaService.render_note_view_ctx(ctx)
        self.assertTrue(isinstance(ctx.note_meta_list, list))


class TestNoteCalendar(_CovBase):

    def test_calendar_page(self):
        self.check_200("/note/calendar")
        self.check_200("/note/calendar?tab=note_create")
        self.check_200("/note/calendar?tab=note_update")
        self.check_200("/note/calendar?date=2024-02")

    def test_calendar_toolbar_tab(self):
        # default branch (no toolbar_tab) + save branch
        self.check_200("/note/calendar")
        self.check_200("/note/calendar?toolbar_tab=none")
        self.check_200("/note/calendar?toolbar_tab=calendar")

    def test_calendar_cell(self):
        c = CalendarCell()
        self.assertEqual(c.date_number, "")
        c2 = CalendarCell(date_number="5", month=3, date_info="x", css_class="c")
        self.assertEqual(c2.date_number, "5")
        self.assertEqual(c2.month, 3)

    def test_calendar_row_is_valid(self):
        row = CalendarRow()
        self.assertFalse(row.is_valid(2))
        c = CalendarCell()
        c.month = 2
        row.append(c)
        self.assertTrue(row.is_valid(2))
        self.assertFalse(row.is_valid(5))

    def test_calendar_get_heads(self):
        handler = NoteCalendarHandler()
        heads = handler.get_heads()
        self.assertEqual(len(heads), 7)
        self.assertTrue(all(isinstance(h, CalendarCell) for h in heads))

    def test_calendar_get_tab(self):
        handler = NoteCalendarHandler()
        tab = handler.get_tab()
        self.assertEqual(tab.tab_key, "tab")

    def test_calendar_get_rows(self):
        handler = NoteCalendarHandler()
        rows = handler.get_rows(__import__("datetime").date(year=2024, month=2, day=1))
        self.assertTrue(isinstance(rows, list))
        self.assertTrue(len(rows) > 0)

    def test_calendar_handle_toolbar_tab_direct(self):
        handler = NoteCalendarHandler()
        kw = Storage()
        user_id = xauth.current_user_id()
        handler.handle_toolbar_tab(kw, user_id=user_id)
        self.assertIn("toolbar_tab", kw)


class TestNoteShare(_CovBase):

    def test_share_page(self):
        note_id = self._new_note("share_page")
        self.check_200("/note/share/edit?action=page&note_id=%s" % note_id)

    def test_share_edit_form(self):
        note_id = self._new_note("share_edit")
        self.check_200("/note/share/edit?action=edit&note_id=%s" % note_id)

    def test_share_save_user_not_exist(self):
        note_id = self._new_note("share_save_ne")
        data = _json.dumps(dict(note_id=note_id, share_to="no_such_user_xyz"))
        resp = json_request_return_dict("/note/share/edit?action=save", method="POST", data=dict(data=data))
        self.assertFalse(resp.get_bool("success"))

    def test_share_save_to_self(self):
        note_id = self._new_note("share_save_self")
        data = _json.dumps(dict(note_id=note_id, share_to="admin"))
        resp = json_request_return_dict("/note/share/edit?action=save", method="POST", data=dict(data=data))
        self.assertFalse(resp.get_bool("success"))

    def test_share_save_success(self):
        note_id = self._new_note("share_save_ok")
        data = _json.dumps(dict(note_id=note_id, share_to="test2"))
        resp = json_request_return_dict("/note/share/edit?action=save", method="POST", data=dict(data=data))
        self.assertTrue(resp.get_bool("success"))

    def test_share_public_and_unshare(self):
        note_id = self._new_note("share_public")
        r1 = json_request_return_dict("/note/share/edit?action=share_public&note_id=%s" % note_id)
        self.assertTrue(r1.get_bool("success"))
        info = note_dao.get_by_id(note_id)
        self.assertEqual(info.is_public, 1)
        r2 = json_request_return_dict("/note/share/edit?action=unshare_public&note_id=%s" % note_id)
        self.assertTrue(r2.get_bool("success"))
        info = note_dao.get_by_id(note_id)
        self.assertEqual(info.is_public, 0)

    def test_share_link_json(self):
        note_id = self._new_note("share_link_json")
        resp = json_request_return_dict(
            "/note/share/edit?action=link_share&_format=json", method="POST",
            data=dict(note_id=note_id))
        self.assertTrue(resp.get_bool("success"))
        self.assertIn("share_token", resp.get_str("data"))

    def test_share_link_form(self):
        note_id = self._new_note("share_link_form")
        self.check_200("/note/share/edit?action=link_share&note_id=%s" % note_id)

    def test_share_delete_not_found(self):
        resp = json_request_return_dict("/note/share/edit?action=delete&share_id=999999999")
        self.assertFalse(resp.get_bool("success"))

    def test_share_delete_success(self):
        note_id = self._new_note("share_del")
        data = _json.dumps(dict(note_id=note_id, share_to="test2"))
        json_request_return_dict("/note/share/edit?action=save", method="POST", data=dict(data=data))
        to_user_id = xauth.UserDao.get_id_by_name("test2")
        share_info = dao_share.get_share_by_note_and_to_user(note_id=note_id, to_user_id=to_user_id)
        self.assertIsNotNone(share_info)
        resp = json_request_return_dict("/note/share/edit?action=delete&share_id=%s" % share_info.id)
        self.assertTrue(resp.get_bool("success"))

    def test_share_aside_html(self):
        from xnote_handlers.note.note_share import ShareEditHandler
        handler = ShareEditHandler()
        html = handler.get_aside_html()
        # xtemplate.render returns bytes (or str); either is acceptable
        self.assertTrue(isinstance(html, (str, bytes)))
