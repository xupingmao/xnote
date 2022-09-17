
import xutils
from xutils import Storage
from . import dao
from . import dao_draft

def update_content(note, new_content, clear_draft = True):
    kw = Storage()
    kw.content = new_content
    kw.version = note.version + 1
    kw.mtime = xutils.format_datetime()
    kw.size = len(new_content)
    dao.update_note(note.id, **kw)

    if clear_draft:
        dao_draft.save_draft(note.id, "")




