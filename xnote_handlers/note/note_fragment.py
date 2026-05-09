from xnote.webui.link import ActionLink, EditFormActionLink, ConfirmActionLink
import xutils
from xnote.core import xauth
from xnote.webui import DataTable, TableActionType, Card, ActionBar, EditFormButton
from xnote.webui import ListView, ListViewItem, BaseContainer, Div
from .models import NoteViewContext
from .dao_fragment import NoteFragmentDao, NoteFragmentRecord
from .dao import NoteIndexDao
from xnote.plugin.table_plugin import BaseTablePlugin
from xutils.base import Storage
from xutils import webutil, dateutil, textutil

def render_note_fragment(ctx: NoteViewContext):
    if ctx.tab != "" and ctx.tab != "all":
        return
    
    note_id = ctx.note_id
    
    list_view = ListView()

    fragments = NoteFragmentDao.list_by_note_id(note_id=note_id)
    for item in fragments:
        edit_url = f"/note/fragment?action=edit&note_id={note_id}&frag_id={item.frag_id}"
        delete_url = f"/note/fragment?action=delete&frag_id={item.frag_id}"
        content_short = textutil.get_short_text(item.content, 50)
        delete_msg = f"确认删除事件【{content_short}】吗"
        
        list_item = ListViewItem(text = f"[{item.date_text}] {item.content}")
        list_item.aside.add(EditFormActionLink(text="编辑", url=edit_url))
        list_item.aside.add(ConfirmActionLink(text="删除", url=delete_url, msg=delete_msg, css_class="danger"))
        list_view.add_item(list_item)
    
    card = Card()
    add_event_link = EditFormActionLink(text="新增事件", url=f"/note/fragment?action=edit&note_id={note_id}", css_class="btn-line-height")
    action_bar = ActionBar(css_class="border-bottom")
    action_bar.aside.css_class = "float-right padding-right-small"
    action_bar.add_span("事件时间线", css_class="bold card-title-span btn-line-height", id="events-timeline")
    action_bar.add_right(add_event_link)
    
    card.add(action_bar)
    card.add(list_view)
    ctx.note_fragment = card


class FragmentHandler(BaseTablePlugin):
    require_admin = False
    require_login = True
    
    def handle_edit(self):
        frag_id = xutils.get_argument_int("frag_id")
        note_id = xutils.get_argument_int("note_id")
        user_id = xauth.current_user_id()
        
        if frag_id > 0:
            frag_record = NoteFragmentDao.get_by_frag_id(frag_id=frag_id, user_id=user_id)
        else:
            frag_record = NoteFragmentRecord()
            frag_record.note_id = note_id
            frag_record.date_text = dateutil.format_date()

        if frag_record is None:
            return "无效的记录"
        
        form = self.create_form()
        form.path = "/note/fragment"
        form.add_row("片段ID", "frag_id", css_class="hide", value=str(frag_id))
        form.add_row("笔记ID", "note_id", readonly=True, value=str(frag_record.note_id))
        form.add_date_input("时间", "date_text", value=frag_record.date_text)
        form.add_textarea("内容", field="content", value=frag_record.content)
        
        kw = Storage()
        kw.form = form
        return self.response_form(**kw)
    
    def handle_save(self):
        param = self.get_param_dict()
        user_id = xauth.current_user_id()
        frag_id = param.get_int("frag_id")
        note_id = param.get_int("note_id")
        
        if frag_id > 0:
            frag_record = NoteFragmentDao.get_by_frag_id(frag_id=frag_id, user_id=user_id)
            if frag_record is None:
                return webutil.FailedResult(code="404", message="记录不存在")
        else:
            frag_record = NoteFragmentRecord()
            frag_record.user_id = user_id
            frag_record.note_id = note_id
            
        note_info = NoteIndexDao.get_by_id(note_id=note_id)
        if note_info is None:
            return webutil.FailedResult(code="404", message="笔记不存在")
        
        frag_record.content = param.get_str("content")
        frag_record.date_text = param.get_str("date_text")

        NoteFragmentDao.save(frag_record)
 
        return webutil.SuccessResult()

    def handle_delete(self):
        frag_id = xutils.get_argument_int("frag_id")
        user_id = xauth.current_user_id()
        NoteFragmentDao.delete_by_id(frag_id=frag_id, user_id=user_id)
        return webutil.SuccessResult()

xurls = (
    "/note/fragment", FragmentHandler,
)