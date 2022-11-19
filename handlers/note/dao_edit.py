
import xutils
from xutils import Storage
from . import dao
from . import dao_draft
from .dao_api import NoteDao

def update_content(note, new_content, clear_draft = True):
    kw = Storage()
    kw.content = new_content
    kw.version = note.version + 1
    kw.mtime = xutils.format_datetime()
    kw.size = len(new_content)

    # 先写日志，再更新数据
    new_note = Storage(**note)
    new_note.content = new_content
    new_note.mtime = kw.mtime
    new_note.version = kw.version

    dao.add_history(note.id, kw.version, new_note)
    dao.update_note(note.id, **kw)

    if clear_draft:
        dao_draft.save_draft(note.id, "")


NoteDao.update_content = update_content

