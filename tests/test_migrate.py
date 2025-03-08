
from . import test_base
from xnote.core import xauth
from xnote_migrate import upgrade_010
from .test_note import create_note_for_test, delete_note_for_test
from xutils import dbutil
from handlers.note.dao_tag import NoteTagBindDao
from xnote_migrate.base import get_upgrade_log_table

app          = test_base.init()
json_request = test_base.json_request
request_html = test_base.request_html
BaseTestCase = test_base.BaseTestCase

class TestMain(BaseTestCase):

    def test_upgrade_010(self):
        get_upgrade_log_table().delete("20230205_note_tag")
        db = dbutil.get_table("note_tags")
        delete_note_for_test("test-md")
        tag_list = ["oldtag1", "oldtag2"]

        note_id = create_note_for_test(type="md", name="test-md")
        user_name = xauth.current_name_str()
        tag_bind = upgrade_010.TagBind()
        tag_bind.note_id = str(note_id)
        tag_bind.user = user_name
        tag_bind.tags = tag_list
        db.insert(tag_bind)

        broken_bind = upgrade_010.TagBind()
        broken_bind.note_id = "123456"
        broken_bind.user = "nobody"
        broken_bind.tags = tag_list
        db.insert(broken_bind)

        upgrade_010.do_upgrade()

        user_id = xauth.current_user_id()
        tag_binds = NoteTagBindDao.get_by_note_id(user_id=user_id, note_id=note_id)

        assert len(tag_binds) == 2
        assert tag_binds[0].tag_code in tag_list
        assert tag_binds[1].tag_code in tag_list

