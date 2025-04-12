# encoding=utf-8
import xutils
from xutils import Storage
from xnote.plugin.table_plugin import BaseTablePlugin
from xnote.plugin import FormRowType
from .dao_relation import NoteRelationDao, NoteRelationDO
from .dao import NoteIndexDao, list_path
from xnote.core import xauth
from xutils import webutil
from .note_service import NoteRelationService

class NoteRelationHandler(BaseTablePlugin):

    require_login = True
    title = "笔记关系编辑"
    
    EDIT_HTML = """
<div class="card">
    {% include common/form/form.html %}
</div>

<script>
xnote.execute(function() {
    console.log("init", "{{select_id}}");
    var parent = $("#{{select_id}}").parents(".layui-layer-content");

    $('#{{select_id}}').select2({
        dropdownParent: parent,
        ajax: {
            url: '/note/api/select_name',
            data: function (params) {
                var query = {
                    search: params.term,
                    type: 'public'
                }

                // Query parameters will be ?search=[term]&type=public
                return query;
            }
        }
    });
});
</script>
"""

    PAGE_HTML = """
<div class="card">
    {% include note/component/note_path.html %}
</div>

<div class="card">
    <div class="table-action-row">
        <button class="btn" onclick="xnote.table.handleEditForm(this)"
            data-url="/note/relation?action=edit&note_id={{file.id}}" 
            data-title="{{create_btn_text}}">{{create_btn_text}}</button>
    </div>
    {% include common/table/table.html %}
</div>
"""

    def handle_page(self):
        note_id = xutils.get_argument_int("note_id")
        user_id = xauth.current_user_id()
        note_index = NoteIndexDao.get_by_id(note_id=note_id, creator_id=user_id, check_user=True)
        if note_index is None:
            return "笔记不存在"
        kw = Storage()
        kw.create_btn_text = "创建关系"
        kw.file = note_index
        kw.pathlist = list_path(file=note_index)
        kw.table = NoteRelationService.get_table(note_id=note_id, user_id=user_id)
        return self.response_page(**kw)

    def handle_edit(self):
        relation_id = xutils.get_argument_int("relation_id")
        note_id = xutils.get_argument_int("note_id")
        user_id = xauth.current_user_id()
        relation = NoteRelationDO()

        if relation_id > 0:
            relation = NoteRelationDao.get_by_id(relation_id=relation_id, user_id=user_id)
        
        if relation is None:
            return "无效的关系"

        note_name = ""
        if relation.target_id > 0:
            note_name = NoteIndexDao.get_note_name(note_id=relation.target_id, creator_id=user_id)


        form = self.create_form()
        form.path = "/note/relation"
        form.add_row("关系ID", "relation_id", readonly=True, value=str(relation_id))
        form.add_row("笔记ID", "note_id", readonly=True, value=str(note_id))
        form.add_row("关系名称", "relation_name", value=relation.relation_name)
        row = form.add_row("关联笔记", "target_id", type=FormRowType.select, value=str(relation.target_id))
        if note_name != "":
            row.add_option(title=note_name, value=str(relation.target_id))
        
        kw = Storage()
        kw.form = form
        kw.select_id = row.id
        return self.response_form(**kw)
    
    def handle_save(self):
        param = self.get_param_dict()
        user_id = xauth.current_user_id()
        relation_id = param.get_int("relation_id")
        if relation_id > 0:
            relation = NoteRelationDao.get_by_id(relation_id=relation_id, user_id=user_id)
            if relation is None:
                return webutil.FailedResult(code="404", message="记录不存在")
        else:
            relation = NoteRelationDO()
            relation.user_id = user_id
        
        relation.note_id = param.get_int("note_id")
        relation.relation_name = param.get_str("relation_name")
        relation.target_id = param.get_int("target_id")

        NoteRelationDao.save(relation)
 
        return webutil.SuccessResult()
    
    def handle_delete(self):
        relation_id = xutils.get_argument_int("relation_id")
        user_id = xauth.current_user_id()
        relation = NoteRelationDao.get_by_id(relation_id=relation_id, user_id=user_id)
        if relation is None:
            return webutil.FailedResult(code="404", message="记录不存在")
        NoteRelationDao.delete(relation)
        return webutil.SuccessResult()

xurls = (
    r"/note/relation", NoteRelationHandler,
)