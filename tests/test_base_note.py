from xnote.core import xauth
from xnote_handlers.note import dao as note_dao
from xnote_handlers.note import dao_delete
from xnote_handlers.note.dao import get_by_id, get_by_name
from tests.test_base import json_request_return_dict

def delete_note_for_test(name=""):
    # 调用2次彻底删除
    user_id = xauth.current_user_id()
    note_index = note_dao.NoteIndexDao.get_by_name(creator_id=user_id, name=name)
    if note_index != None:
        dao_delete.delete_note_physically(note_index.creator, note_index.id)


def get_default_group_id():
    name = "default_group_id"
    note = get_by_name(xauth.current_name_str(), name)
    if note != None:
        return note.id
    return create_note_for_test("group", name)

def create_note_for_test(type="", name="", *, content = "", tags="", parent_id=0) -> int:
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
    
    resp_data = note_result.get_dict("data")
    note_id = resp_data.get_int("id")
    print("新笔记id:", note_id)
    assert isinstance(note_id, int)
    return note_id
