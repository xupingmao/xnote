# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2026/10/06

"""笔记创建相关处理（从 note_edit.py 拆分出来）

包含:
    /note/create   创建页面（DataForm 渲染，不依赖 html 模板）
    /note/add      同上（历史路径）
    /note/create/check 名称检测历史接口（返回HTML片段）
"""

import web
import time
import typing

from typing import List

import xutils
from xutils import dateutil
from xutils import webutil
from xutils.base import BaseDataRecord

from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xmanager
from xnote.core.xtemplate import T
from xnote.plugin import DataForm, PageEditForm, BaseFormPlugin
from xnote.plugin import TabBox, Card
from xnote.webui import TextLink
from xnote.webui import TagSelect

from xnote_handlers.config import AsideConfig
from .constant import *
from . import dao as note_dao
from . import note_helper
from .dao import NoteIndexDao
from .dao_category import refresh_category_count
from .dao_tag import NoteTagBindDao


class CreateNoteContext(BaseDataRecord):
    def __init__(self, **kw):
        self.method = ""
        self.date = ""
        self.creator_id = 0
        self.update(kw)


def get_heading_by_type(type):
    title = u"创建" + NOTE_TYPE_DICT.get(type, u"笔记")
    return T(title)


def create_log_func(note: note_dao.NoteDO, ctx: CreateNoteContext):
    method   = ctx.method
    date_str: str = ctx.date

    if method != "POST":
        # GET请求直接返回
        return

    if date_str is None or date_str == "":
        date_str = time.strftime("%Y-%m-%d")
    note.name = u"日志:" + date_str + dateutil.convert_date_to_wday(date_str)
    return note_dao.create_note(note, date_str)


def default_create_func(note: note_dao.NoteDO, ctx: CreateNoteContext):
    method   = ctx.method
    date_str = ctx.date
    name     = note.name

    if method != "POST":
        # GET请求直接返回
        return

    if name == "":
        message = '标题为空'
        raise Exception(message)

    return note_dao.create_note(note, date_str)


CREATE_FUNC_DICT = {
    "log.bak": create_log_func
}


CHECK_NOTES_HTML = """
{% if len(notes) == 0 %}
    <span>无相似笔记</span>
{% end %}
{% for note in notes %}
    <a href="{{note.url}}">{{note.name}}</a><br/>
{% end %}
"""
CHECK_NOTES_CODE = xtemplate.compile_template(CHECK_NOTES_HTML, "note.check")


def render_check_notes_html(notes) -> str:
    """渲染相似笔记列表（创建页面的名称检测用）"""
    result = CHECK_NOTES_CODE.generate(notes=notes)
    if isinstance(result, bytes):
        return result.decode("utf-8")
    return result


def format_name_by_date(date_str: str) -> str:
    """按日期生成标题: 日期 + 星期（日期解析失败时只用日期）"""
    if date_str == "":
        return ""
    try:
        return date_str + dateutil.convert_date_to_wday(date_str)
    except Exception:
        return date_str


class NoteCreateHandler(BaseFormPlugin):
    """创建笔记页面：表单用 DataForm 渲染，不依赖任何 html 模板文件

    请求约定:
        GET  /note/create                    创建页面（类型tab + 表单）
        POST /note/create                    兼容历史接口: 直接按表单参数创建
        POST /note/create?action=save        DataForm 提交创建
        POST /note/create?action=check       标题重复检测（返回渲染命令）
        POST /note/create?action=fill_name   选择日期后回填标题（返回渲染命令）
        POST /note/create?action=reload_tags 切换笔记本后刷新标签（返回渲染命令）
    """

    require_admin = False
    require_login = True
    show_search = False
    title = T("创建笔记")

    # 标签行的 row.id；ajax 局部刷新替换的是它的行值容器（row.id + "-value"）
    TAG_ROW_ID = "note-create-tags"
    CHECK_BOX_ID = "note-create-check"

    def create_form(self) -> DataForm:
        return PageEditForm()

    def handle(self, input=""):
        action = xutils.get_argument_str("action")
        if action == "":
            # 兼容历史接口: 直接POST表单参数创建（/note/add 等旧调用方）
            if web.ctx.method == "POST":
                return self.handle_create_by_params()
            return self.handle_page()

        method = getattr(self, "handle_" + action, None)
        if method is None:
            return webutil.FailedResult(message=f"不支持的操作: {action}")
        return method()

    # ------------------------------------------------------------------
    # 页面
    # ------------------------------------------------------------------
    def handle_page(self):
        note_type = xutils.get_argument_str("type", "md")
        parent_id = xutils.get_argument_int("parent_id")
        name = xutils.get_argument_str("name", "")
        date = xutils.get_argument_str("date", "")

        self.show_aside = True
        self.aside_html = AsideConfig.note_aside_html
        self.parent_link = self.get_parent_link(parent_id)

        form = self.create_form()
        form.path = "/note/create"
        form.model_name = "note"

        form.add_hidden_input("type", value=note_type)
        tab = form.add_tab_box(title="类型", tab_key="type", value=note_type or "md", css_class="btn-style")
        assert tab.tab_box != None
        
        for type_info in NOTE_TYPE_LIST:
            if type_info.visible:
                tab.tab_box.add_item(title=type_info.name, value=type_info.type)
                        
        form.add_input("标题", "name", value=name,
                       oninput_ajax_url="/note/create?action=check")

        date_row = form.add_date_input("日期", "date", value=date or dateutil.format_date())
        # 选完日期自动回填标题（历史行为: 日志类笔记的标题就是 日期+星期）
        date_row.oninput_ajax_url = "/note/create?action=fill_name"

        group_row = self.add_group_row(form, parent_id)
        group_row.oninput_ajax_url = "/note/create?action=reload_tags"

        self.add_tag_row(form, parent_id)
        self.add_check_row(form)

        self.render_form(form)

    def get_parent_link(self, parent_id: int):
        """上级链接: 指定了笔记本时指向该笔记本"""
        if parent_id <= 0:
            return None
        parent_note = note_dao.get_by_id_and_creator_id(
            note_id=parent_id, creator_id=xauth.current_user_id())
        if parent_note is None:
            return None
        return TextLink(text=parent_note.name, href=parent_note.url)

    def add_group_row(self, form: DataForm, parent_id: int):
        """笔记本下拉（按 置顶/一级目录/其它父目录 分组）"""
        group_list = note_dao.list_group_v2(xauth.current_name_str(), orderby="name")
        converter = note_helper.NoteGroupConverter(group_list)

        row = form.add_select("笔记本", "parent_id", value=str(parent_id))
        for opt_group in converter.get_opt_groups():
            group = row.add_opt_group(opt_group.label)
            for item in opt_group.children:
                group.add_option(item.name, str(item.id))
        return row

    def add_tag_row(self, form: DataForm, parent_id: int):
        row = form.add_tag_select("标签", "tags", multiple=True)
        # 固定id: 切换笔记本后由 action=reload_tags 局部刷新这个容器
        row.id = self.TAG_ROW_ID
        for tag_name in self.list_tag_names(parent_id):
            row.add_option(tag_name, tag_name)
        return row

    def add_check_row(self, form: DataForm):
        """名称检测的结果容器，内容由 action=check 回填"""
        form.add_html(f'<div id="{self.CHECK_BOX_ID}"></div>', title="名称检测")

    def list_tag_names(self, parent_id: int) -> List[str]:
        """笔记本下已有的标签"""
        if parent_id <= 0:
            return []
        user_id = xauth.current_user_id()
        tag_list = NoteTagBindDao.list_by_note_id(user_id=user_id, note_id=parent_id)
        return [tag.tag_name for tag in tag_list]

    # ------------------------------------------------------------------
    # 提交: DataForm
    # ------------------------------------------------------------------
    def handle_save(self):
        param = self.get_param_dict()
        try:
            self.check_parent_exists(param.get_int("parent_id"))
            created_note = self.do_create_note(
                name=param.get_str("name"),
                type0=param.get_str("type", "md"),
                parent_id=param.get_int("parent_id"),
                date=param.get_str("date", ""),
                tags=param.get_str("tags", ""),
                content=param.get_str("content", ""))
        except Exception as e:
            xutils.print_exc()
            return webutil.FailedResult(message=str(e))

        if created_note is None:
            return webutil.FailedResult(message="创建笔记失败")

        result = self.after_create(created_note)
        return webutil.SuccessResult(data=dict(id=created_note.id),
                                     redirect_url=result.url)

    # ------------------------------------------------------------------
    # 提交: 历史接口（表单参数直接POST）
    # ------------------------------------------------------------------
    def handle_create_by_params(self):
        name = xutils.get_argument_str("name")
        tags = xutils.get_argument_str("tags", "")
        content = xutils.get_argument_str("content", "")
        type0 = xutils.get_argument_str("type", "md")
        date = xutils.get_argument_str("date", "")
        format = xutils.get_argument_str("_format", "")
        parent_id = xutils.get_argument_int("parent_id")
        default_name = xutils.get_argument_str("default_name")

        if name == "":
            name = default_name

        # 历史行为: 笔记本不存在时直接抛异常（接口返回500），所以放在try外面
        self.check_parent_exists(parent_id)

        try:
            created_note = self.do_create_note(name=name, type0=type0, parent_id=parent_id,
                                               date=date, tags=tags, content=content)
        except Exception as e:
            xutils.print_exc()
            if format == "json":
                return webutil.FailedResult(code="fail", message=str(e))
            raise e

        if created_note is None:
            return webutil.FailedResult(code="fail", message="创建笔记失败")

        return self.after_create(created_note)

    def do_create_note(self, name="", type0="md", parent_id=0, date="", tags="", content="") -> note_dao.NoteDO:
        """校验并创建笔记，返回创建后的笔记（失败抛异常）"""
        user_info = xauth.current_user()
        assert user_info != None
        creator = user_info.name
        creator_id = user_info.id

        xmanager.add_visit_log(creator, "/note/create")

        type = NOTE_TYPE_MAPPING.get(type0, type0)

        note = note_dao.NoteDO()
        note.name = name
        note.creator = creator
        note.creator_id = creator_id
        note.parent_id = parent_id
        note.type = type
        note.content = content
        note.data = ""
        note.size = len(content)
        note.is_public = 0
        note.priority = 0
        note.version = 0
        note.is_deleted = 0
        # 标签可能来自 tag 选择器（逗号分隔）或历史调用方（空格分隔）
        note.tags = tags.replace(",", " ").replace("，", " ").split()
        note.level = 0

        if note.parent_id < 0:
            note.priority = -1
            note.level = -1

        ctx = CreateNoteContext(method="POST", date=date, creator_id=creator_id)
        self.check_before_create(ctx, note)

        create_func = CREATE_FUNC_DICT.get(type, default_create_func)
        inserted_id = create_func(note, ctx)
        if inserted_id is None:
            raise Exception("create not failed, inserted_id is None")

        new_note = note_dao.get_by_id_and_creator_id(inserted_id, creator_id)
        if new_note is None:
            raise Exception("created not not found")
        
        return new_note

    # ------------------------------------------------------------------
    # 表单联动（返回渲染命令，前端交给 xnote.executeCommands 执行）
    # ------------------------------------------------------------------
    def handle_check(self):
        """标题重复检测"""
        name = xutils.get_argument_str("value")
        result = webutil.CommandsResult()

        if name == "":
            result.add_command(command="update_html", id=self.CHECK_BOX_ID, value="请输入标题")
            return result

        user_id = xauth.current_user_id()
        notes = NoteIndexDao.list(creator_id=user_id, name_like=f"%{name}%", limit=5)
        result.add_command(command="update_html", id=self.CHECK_BOX_ID,
                           value=render_check_notes_html(notes))
        return result

    def handle_fill_name(self):
        """选择日期后回填标题: 日期 + 星期"""
        date_str = xutils.get_argument_str("value")
        result = webutil.CommandsResult()

        if date_str == "":
            return result

        result.add_command(command="update_value", name="name",
                           value=format_name_by_date(date_str))
        return result

    def handle_reload_tags(self):
        """切换笔记本后刷新可选标签

        整棵控件重建（不含外层 .form-row-value，它的id就是锚点），id 的
        -value 后缀与 FormRow.render 的行容器对应。
        """
        parent_id = xutils.get_argument_int("value")
        tag_select = TagSelect(name="tags", value="", multiple=True,
                               css_class="form-tag-select")
        for tag_name in self.list_tag_names(parent_id):
            tag_select.add_option(tag_name, tag_name)

        result = webutil.CommandsResult()
        result.add_command(command="update_html", id=self.TAG_ROW_ID + "-value",
                           value=tag_select.render())
        result.add_command(command="xnote.refresh")
        return result

    # ------------------------------------------------------------------
    # 公共逻辑
    # ------------------------------------------------------------------
    def check_parent_exists(self, parent_id: int):
        """笔记本必须存在（不存在时抛异常）"""
        if parent_id <= 0:
            return
        creator_id = xauth.current_user_id()
        parent_note = note_dao.get_by_id_and_creator_id(note_id=parent_id, creator_id=creator_id)
        if not parent_note:
            raise Exception(f"parent note not found, parent_id = {parent_id}")

    def check_before_create(self, ctx: CreateNoteContext, note: note_dao.NoteDO):
        if ctx.method == "GET":
            return

        type = note.type
        if type not in VALID_NOTE_TYPE_SET:
            raise Exception(f"无效的类型: {type}")

        if note.name == "":
            raise Exception("标题为空")

        name = note.name
        check_by_name = note_dao.get_by_name(note.creator, name)
        if check_by_name != None:
            message = u"笔记【%s】已存在" % name
            raise Exception(message)

        if not note.is_group:
            if note.parent_id == 0:
                message = u"请选择笔记本"
                raise Exception(message)

    def after_create(self, created_note: note_dao.NoteDO):
        note_type = created_note.type
        if created_note.type == "group":
            refresh_category_count(created_note.creator, created_note.category)

        inserted_id = created_note.id
        if note_type == "group":
            redirect_url = created_note.get_url()
        else:
            redirect_url = created_note.get_edit_url()

        resp = webutil.SuccessResult(data = dict(id=inserted_id, url=redirect_url))
        # 兼容历史接口
        resp.id = inserted_id
        resp.url = redirect_url
        return resp


class CheckCreateHandler:
    """名称检测的历史接口（返回HTML片段），页面内的检测走
    NoteCreateHandler 的 action=check（返回渲染命令）"""

    @xauth.login_required()
    def POST(self):
        name = xutils.get_argument_str("name")
        if name == "":
            return "请输入标题"
        user_id = xauth.current_user_id()
        name_like = "%" + name + "%"
        notes = NoteIndexDao.list(creator_id=user_id, name_like=name_like, limit=5)
        return render_check_notes_html(notes)


xurls = (
    r"/note/add"         , NoteCreateHandler,
    r"/note/create"      , NoteCreateHandler,
    r"/note/create/check", CheckCreateHandler,
)
