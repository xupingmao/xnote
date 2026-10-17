
import xutils
from xnote.plugin import TextLink, sidebar, RawHtml
from xnote.plugin import TableActionType
from xnote.plugin.table_plugin import BaseTablePlugin, FormRowType
from . import dao as note_dao
from .dao import NoteDao, list_path
from xutils import Storage
from xutils import webutil
from . import dao_share
from xnote.core import xauth, xtemplate, xconfig
from .note_edit import check_get_note, NoteException

class ShareEditHandler(BaseTablePlugin):

    require_admin = False
    require_login = True
    show_aside = True

    title = "分享笔记"

    info_html = """
<script type="text/javascript" src="{{_server_home}}/_static/lib/clipboard/clipboard-2.0.4.min.js"></script>
<div class="card">
    {% include note/component/note_path.html %}
</div>

<div class="card">
    <div class="card-text">
        说明：公开分享所有人可见，链接分享仅获取链接的人可见
    </div>
</div>
"""

    copy_link_html = """
<div class="row">
    <span id="share-link-span"></span>
</div>
<input type="hidden" id="share-link-value" value="{{share_link}}">
"""

    copy_footer_html = """
<div class="float-right">
    <button class="btn large copy-link-btn">复制链接</button>
    <button class="btn large btn-default" onclick="xnote.dialog.closeByElement(this)" data-form-id="xnoteForm{{_xnote_form.id}}">关闭</button>
</div>

<script>
xnote.execute(function() {
    var link = window.location.protocol + "//" + window.location.host + $("#share-link-value").val();
    $("#share-link-span").text(link);
    xnote.note.initBtnCopy(".copy-link-btn", link);
});
</script>
"""

    def get_aside_html(self):
        return sidebar.get_default_sidebar_html()

    def handle_page(self):
        note_id = xutils.get_argument_int("note_id")
        note_info = NoteDao.get_by_id(note_id, include_full=False)
        if note_info is None:
            raise Exception("note is empty")

        share_list = dao_share.list_share_by_note_id(note_id)
        
        table = self.create_table()
        table.default_head_style.min_width = "100px"
        table.add_head(title="被分享人", field="to_user")
        table.add_head(title="分享时间", field="ctime")
        table.add_action("删除", link_field="delete_url", type=TableActionType.confirm, msg_field="delete_msg", css_class="btn danger")

        table.action_bar.add_edit_button(text="新增分享", url=f"?action=edit&note_id={note_id}")

        if note_info.is_public:
            table.action_bar.add_confirm_button(text="取消公开分享", 
                                                message="确认取消公开分享吗?",
                                                url=f"?action=unshare_public&note_id={note_id}", css_class="btn-default")
        else:
            table.action_bar.add_confirm_button(text="公开分享", 
                                                message="确认公开分享吗?",
                                                url=f"?action=share_public&note_id={note_id}", css_class="btn-default")

        table.action_bar.add_edit_button(text="链接分享", url=f"?action=link_share&note_id={note_id}", css_class="btn-default")

        for share_info in share_list:
            share_info.delete_url = f"?action=delete&share_id={share_info.id}"
            share_info.delete_msg = f"确认取消给[{share_info.to_user}]的分享吗?"
            table.add_row(share_info)

        kw = Storage()
        kw.table = table
        kw.file = note_info
        kw.pathlist = list_path(file=note_info)

        self.writehtml(self.info_html, **kw)

        return self.response_page(**kw)
    
    def handle_edit(self):
        note_id = xutils.get_argument_int("note_id")
        form = self.create_form()
        form.add_row(field="note_id", css_class="hide", value=str(note_id))
        form.add_row(title="用户名", field="share_to")

        kw = Storage()
        kw.form = form
        return self.response_form(**kw)
    
    def handle_save(self):
        param = self.get_param_dict()
        note_id = param.get_int("note_id")
        share_to = param.get_str("share_to")
        note = check_get_note(note_id)

        if not xauth.is_user_exist(share_to):
            return webutil.FailedResult(code = "fail", message = "用户[%s]不存在" % share_to)

        share_from = xauth.current_name_str()
        if share_to == share_from:
            return webutil.FailedResult(code = "fail", message = "不需要分享给自己")

        dao_share.share_note_to(note.id, share_from, share_to)

        return webutil.SuccessResult()

    
    def handle_delete(self):
        share_id = xutils.get_argument_int("share_id")
        share_info = dao_share.NoteShareDao.get_by_id(share_id)
        if share_info is None:
            return webutil.FailedResult(code="404", message="分享不存在")
        
        note_id = share_info.target_id
        try:
            check_get_note(note_id)
            dao_share.NoteShareDao.delete_by_id(share_id)
            return webutil.SuccessResult()
        except NoteException as e:
            return webutil.FailedResult(code=e.code, message=e.message)
        
    def handle_share_public(self):
        note_id = xutils.get_argument_int("note_id")

        try:
            note_info = check_get_note(note_id)        
            share_info = note_dao.ShareInfoDO()
            share_info.share_type=note_dao.ShareTypeEnum.note_public.value
            share_info.target_id = note_id
            share_info.from_id = note_info.creator_id
            note_dao.ShareInfoDao.insert_ignore(share_info)
            note_dao.update_note(note_id, is_public = 1)
        except NoteException as e:
            return webutil.FailedResult(code=e.code, message=e.message)
        
        return webutil.SuccessResult()
    
    def handle_unshare_public(self):
        note_id = xutils.get_argument_int("note_id")

        try:
            check_get_note(note_id)        
            note_dao.update_note(note_id, is_public = 0)
            note_dao.ShareInfoDao.delete_by_target(share_type="note_public", target_id=note_id)
        except NoteException as e:
            return webutil.FailedResult(code=e.code, message=e.message)
        
        return webutil.SuccessResult()

    def handle_link_share(self):
        note_id = xutils.get_argument_int("note_id")

        note = check_get_note(note_id)
        NoteTokenDao = dao_share.NoteTokenDao

        if note.token != None and note.token != "":
            NoteTokenDao.update_token(note)
            share_link = f"{xconfig.WebConfig.server_home}/note/view?share_token={note.token}"
        else:
            token = NoteTokenDao.create_token(note.id)
            note_dao.update_note(note.id, token = token)
            share_link = f"{xconfig.WebConfig.server_home}/note/view?share_token={token}"

        if self.get_format() == "json":
            return webutil.SuccessResult(data=share_link)

        form = self.create_form()
        form.save_btn_css = "hide"
        form.add_row(field="note_id", css_class="hide", value=str(note_id))
        html = xtemplate.render_text(self.copy_link_html, share_link = share_link)
        form.add_html(html)
        form.set_footer(RawHtml(xtemplate.render_text(self.copy_footer_html, _xnote_form = form)))

        kw = Storage()
        kw.form = form
        return self.response_form(**kw)

xurls = (
    r"/note/share/edit", ShareEditHandler,
)