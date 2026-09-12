# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2026/09/12
# 待办 / 项目 页面处理器（基于 BaseListPlugin + ListView 服务端渲染）
import xutils
import web
import math

from typing import Dict, List, Optional, Union
from xutils import Storage, webutil
from xnote.core import xauth, xtemplate
from xnote.core.xtemplate import T
from xnote.plugin import (
    ListViewItem, EditFormActionLink, EditFormButton,
    ConfirmActionLink, AjaxActionLink, TextTag, FormRowType, TabBox, Div,
    TextLink)
from xnote.plugin.list_plugin import BaseListPlugin
from xnote_handlers.config import AsideConfig, LinkConfig
from xutils.textutil import mark_text

from .dao import TodoDao, ProjectDao
from .todo_model import (
    TodoRecord, TodoStatusEnum, TodoPriorityEnum,
    parse_time_ms, format_time_ms, format_date_ms)
from .project_model import ProjectRecord, ProjectStatusEnum
from .todo_comment import to_comment_target_id


TODO_PAGE_PATH = "/todo"

# 优先级 -> tag 样式
PRIORITY_TAG_CLASS = {
    TodoPriorityEnum.low.value: "gray",
    TodoPriorityEnum.normal.value: "lightblue",
    TodoPriorityEnum.high.value: "orange",
    TodoPriorityEnum.urgent.value: "red",
}

# 状态 -> tag 样式
STATUS_TAG_CLASS = {
    TodoStatusEnum.not_started.value: "lightgray",
    TodoStatusEnum.in_progress.value: "lightblue",
    TodoStatusEnum.done.value: "gray",
    TodoStatusEnum.canceled.value: "gray",
}

# 状态筛选的特殊值
STATUS_FILTER_PENDING = "pending"  # 【待办】= 未开始 + 进行中
STATUS_FILTER_ALL = "all"          # 【全部】= 不过滤
PENDING_STATUS_LIST = [TodoStatusEnum.not_started.value, TodoStatusEnum.in_progress.value]

# 项目状态 -> tag 样式
PROJECT_STATUS_TAG_CLASS = {
    ProjectStatusEnum.active.value: "",
    ProjectStatusEnum.archived.value: "gray",
}


def _render_component(component) -> str:
    html = component.render()  # type: Union[str, bytes]
    if isinstance(html, bytes):
        return html.decode("utf-8")
    return html


def _enum_label_map(enum_cls) -> Dict[str, str]:
    return {e.value: e.name for e in enum_cls.enums()}


def _build_filter_html(project_id: str, status: str, priority: str) -> str:
    """状态/优先级筛选 Tab，href 互相保留筛选参数"""
    status_tab = TabBox(tab_key="status", title=T("状态"),
                        tab_default=STATUS_FILTER_PENDING, css_class="btn-style")
    status_tab.add_item(title=T("待办"), value=STATUS_FILTER_PENDING,
                        href="/todo?project_id=%s&status=%s&priority=%s" % (project_id, STATUS_FILTER_PENDING, priority))
    status_tab.add_item(title=T("全部"), value=STATUS_FILTER_ALL,
                        href="/todo?project_id=%s&status=%s&priority=%s" % (project_id, STATUS_FILTER_ALL, priority))
    for e in TodoStatusEnum.enums():
        status_tab.add_item(title=e.name, value=e.value,
                            href="/todo?project_id=%s&status=%s&priority=%s" % (project_id, e.value, priority))

    priority_tab = TabBox(tab_key="priority", title=T("优先级"), css_class="btn-style")
    priority_tab.add_item(title=T("全部"), value="",
                          href="/todo?project_id=%s&status=%s" % (project_id, status))
    for e in TodoPriorityEnum.enums():
        priority_tab.add_item(title=e.name, value=e.value,
                              href="/todo?project_id=%s&status=%s&priority=%s" % (project_id, status, e.value))

    return _render_component(status_tab) + _render_component(priority_tab)


def _build_project_filter_html(status: str) -> str:
    """项目状态筛选 Tab"""
    current = status or ProjectStatusEnum.active.value
    status_tab = TabBox(tab_key="status", title=T("状态"), tab_default=current, css_class="btn-style")
    for e in ProjectStatusEnum.enums():
        status_tab.add_item(title=e.name, value=e.value, href="/todo?status=%s" % e.value)
    return _render_component(status_tab)


class _TodoListPlugin(BaseListPlugin):
    """待办/项目列表基类，列表上方可渲染筛选 Tab"""
    require_login = True
    require_admin = False
    page_html = """
{% include common/script/load_select2.html %}
{% include common/script/load_laydate.html %}

{% init filter_html = "" %}
{% init list_view = None %}

{% if filter_html %}
<div class="card">
    {% raw filter_html %}
</div>
{% end %}

{% if list_view %}
<div class="card">
    {% render list_view %}
</div>
{% end %}

{% if page_max > 1 %}
<div class="card row padding-top-md padding-bottom-md">
    {% include common/pagination.html %}
</div>
{% end %}
"""


class ProjectListPlugin(_TodoListPlugin):
    """项目列表（待办首页）"""
    title = T("项目")
    parent_link = LinkConfig.app_index

    def handle_page(self):
        user_id = xauth.current_user_id()
        status = xutils.get_argument_str("status", "") or ProjectStatusEnum.active.value
        status_labels = _enum_label_map(ProjectStatusEnum)
        # 一次分组查询拿到每个项目的状态计数
        count_map = TodoDao.count_group_by_project(user_id, is_deleted=0)

        # 分页
        page = xutils.get_argument_int("page", 1)
        page_size = 50
        offset = max(0, page - 1) * page_size
        projects = ProjectDao.list_by_user(user_id, status=status,
                                           offset=offset, limit=page_size)
        total = ProjectDao.count_by_user(user_id, status=status)
        page_max = max(1, int(math.ceil(total / page_size)))

        list_view = self.create_list_view()
        for project in projects:
            bucket = count_map.get(project.project_id, {})
            pending_count = bucket.get(TodoStatusEnum.not_started.value, 0) + \
                bucket.get(TodoStatusEnum.in_progress.value, 0)
            done_count = bucket.get(TodoStatusEnum.done.value, 0)

            href = "/todo?project_id=%s" % project.project_id
            # 整行可点击：外层 <a>；操作区(extra)由 ListViewItem 渲染在 <a> 之外并浮动到右侧
            item = ListViewItem(icon_class="fa fa-folder-o", href=href, show_chevron_right=True)
            item.add_span(text=project.name, css_class="bold")
            item.tags.append(TextTag(text=status_labels.get(project.status, project.status),
                                     css_class=PROJECT_STATUS_TAG_CLASS.get(project.status, "gray")))
            item.tags.append(TextTag(text=T("待办 %s") % pending_count, css_class="lightblue"))
            item.tags.append(TextTag(text=T("完成 %s") % done_count, css_class="gray"))

            item.extra.add(EditFormActionLink(
                text=T("编辑"), url="?action=edit&model=project&project_id=%s" % project.project_id))
            item.extra.add(ConfirmActionLink(
                text=T("删除"), url="?action=delete&model=project&project_id=%s" % project.project_id,
                msg=T("确定删除项目【%s】吗?") % project.name))
            list_view.add_item(item)

        self.option_html = EditFormButton(text=T("新建项目"), url="?action=edit&model=project").render()
        self.update_aside(AsideConfig.default_aside_html)
        filter_html = _build_project_filter_html(status)
        return self.response_page(list_view=list_view, filter_html=filter_html,
                                  page=page, page_max=page_max, page_total=total, page_size=page_size)

    def handle_edit(self):
        user_id = xauth.current_user_id()
        project_id = xutils.get_argument_int("project_id", 0)
        project = ProjectDao.get_by_id(project_id, user_id=user_id) if project_id != 0 else None

        form = self.create_form()
        form.path = TODO_PAGE_PATH
        form.model_name = "project"
        form.id = "project_edit"
        form.add_row(title="", field="project_id", value=str(project_id), css_class="hide")
        form.add_row(title=T("名称"), field="name", value=project.name if project else "",
                     placeholder=T("项目名称"))
        form.add_row(title=T("描述"), field="desc", value=project.desc if project else "",
                     type=FormRowType.textarea)
        status_row = form.add_row(title=T("状态"), field="status", type=FormRowType.select,
                                  value=project.status if project else ProjectStatusEnum.active.value)
        for e in ProjectStatusEnum.enums():
            status_row.add_option(e.name, e.value)
        return self.response_form(form=form)

    def handle_save(self):
        user_id = xauth.current_user_id()
        data = self.get_data_dict()
        project_id = data.get_int("project_id", 0)
        name = data.get_str("name", "")
        desc = data.get_str("desc", "")
        status = data.get_str("status", ProjectStatusEnum.active.value)
        if name == "":
            return webutil.FailedResult(message="项目名称不能为空")

        if project_id == 0:
            project = ProjectRecord()
            project.user_id = user_id
            project.name = name
            project.desc = desc
            project.status = status
            ProjectDao.create(project)
        else:
            project = ProjectDao.get_by_id(project_id, user_id=user_id)
            if project is None:
                return webutil.FailedResult(message="项目不存在")
            project.name = name
            project.desc = desc
            project.status = status
            ProjectDao.update(project)
        return webutil.SuccessResult()

    def handle_delete(self):
        user_id = xauth.current_user_id()
        project_id = xutils.get_argument_int("project_id", 0)
        ProjectDao.delete(project_id, user_id=user_id)
        return webutil.SuccessResult()


class TaskListPlugin(_TodoListPlugin):
    """某个项目下的待办列表"""
    title = T("待办")
    parent_link = LinkConfig.task_list

    def handle_page(self):
        user_id = xauth.current_user_id()
        project_id = xutils.get_argument_int("project_id", 0)
        status = xutils.get_argument_str("status", STATUS_FILTER_PENDING)
        priority = xutils.get_argument_str("priority", "")

        status_labels = _enum_label_map(TodoStatusEnum)
        priority_labels = _enum_label_map(TodoPriorityEnum)

        # 状态筛选：【待办】= 未开始+进行中；【全部】= 不过滤；其它 = 单状态
        status_list = None  # type: Optional[List[str]]
        status_filter = None  # type: Optional[str]
        if status == STATUS_FILTER_ALL:
            pass
        elif status == "" or status == STATUS_FILTER_PENDING:
            status_list = PENDING_STATUS_LIST
        else:
            status_filter = status

        # 分页
        page = xutils.get_argument_int("page", 1)
        page_size = 50
        offset = max(0, page - 1) * page_size

        tasks = TodoDao.list_with_filters(
            user_id, project_id=project_id, status=status_filter, status_list=status_list,
            priority=priority or None, sort="create_time_desc", offset=offset, limit=page_size)
        total = TodoDao.count_with_filters(
            user_id, project_id=project_id, status=status_filter, status_list=status_list,
            priority=priority or None)
        page_max = max(1, int(math.ceil(total / page_size)))

        list_view = self.create_list_view()
        for task in tasks:
            # 两行展示：第一行内容(可点进详情)，第二行左侧标签、右侧操作
            item = ListViewItem(icon_class="fa fa-check-square-o")
            item.add_link(text=task.content, href="/todo/detail?task_id=%s" % task.task_id,
                          css_class="bold")

            meta = Div(css_class="todo-task-meta")
            tag_box = Div(css_class="todo-task-meta-tags")
            tag_box.add(TextTag(
                text=status_labels.get(task.status, task.status),
                css_class=STATUS_TAG_CLASS.get(task.status, "gray")))
            tag_box.add(TextTag(
                text=priority_labels.get(task.priority, task.priority),
                css_class=PRIORITY_TAG_CLASS.get(task.priority, "gray")))
            begin_time = format_time_ms(task.begin_time)
            if begin_time:
                tag_box.add(TextTag(text=begin_time))
            meta.add(tag_box)

            action_box = Div(css_class="todo-task-meta-actions")
            base = "&model=task&project_id=%s&task_id=%s" % (project_id, task.task_id)
            # 状态变更无需确认，直接执行后 toast 结果
            if task.status not in (TodoStatusEnum.done.value, TodoStatusEnum.canceled.value):
                action_box.add(AjaxActionLink(text=T("完成"), url="?action=finish" + base))
            # 未开始之外的状态（含已取消）都支持重开
            if task.status != TodoStatusEnum.not_started.value:
                action_box.add(AjaxActionLink(text=T("重开"), url="?action=reset" + base))
            if task.status != TodoStatusEnum.canceled.value:
                action_box.add(AjaxActionLink(text=T("取消"), url="?action=cancel" + base))
            action_box.add(EditFormActionLink(text=T("编辑"), url="?action=edit" + base))
            action_box.add(ConfirmActionLink(text=T("删除"), url="?action=delete" + base,
                                             msg=T("确定删除该待办吗?")))
            meta.add(action_box)

            item.add(meta)
            list_view.add_item(item)

        self.option_html = EditFormButton(
            text=T("新建待办"), url="?action=edit&model=task&project_id=%s" % project_id).render()
        self.update_aside(AsideConfig.default_aside_html)
        filter_html = _build_filter_html(str(project_id), status, priority)
        return self.response_page(list_view=list_view, filter_html=filter_html,
                                  page=page, page_max=page_max, page_total=total, page_size=page_size)

    def handle_edit(self):
        user_id = xauth.current_user_id()
        project_id = xutils.get_argument_int("project_id", 0)
        task_id = xutils.get_argument_int("task_id", 0)
        task = TodoDao.get_by_id(task_id, user_id=user_id) if task_id != 0 else None

        form = self.create_form()
        form.path = TODO_PAGE_PATH
        form.model_name = "task"
        form.id = "task_edit"
        form.add_row(title="", field="task_id", value=str(task_id), css_class="hide")
        form.add_textarea(title=T("内容"), field="content", value=task.content if task else "",
                          placeholder=T("待办内容"), rows=3)
        row = form.add_row(title=T("优先级"), field="priority", type=FormRowType.select,
                           value=task.priority if task else TodoPriorityEnum.normal.value)
        for e in TodoPriorityEnum.enums():
            row.add_option(e.name, e.value)

        # 所属项目可修改
        current_project_id = task.project_id if task else project_id
        project_row = form.add_row(title=T("所属项目"), field="project_id", type=FormRowType.select,
                                   value=str(current_project_id))
        project_row.add_option(T("未分类"), "0")
        for project in ProjectDao.list_by_user(user_id):
            project_row.add_option(project.name, str(project.project_id))

        form.add_date_input(title=T("开始时间"), field="begin_time",
                            value=format_date_ms(task.begin_time) if task else "")
        form.add_date_input(title=T("结束时间"), field="end_time",
                            value=format_date_ms(task.end_time) if task else "")
        # 完成时间只读展示（由状态变更自动维护）
        form.add_row(title=T("完成时间"), field="done_time",
                     value=format_time_ms(task.done_time) if task else "", readonly=True)
        return self.response_form(form=form)

    def handle_save(self):
        user_id = xauth.current_user_id()
        data = self.get_data_dict()
        task_id = data.get_int("task_id", 0)
        project_id = data.get_int("project_id", 0)
        content = data.get_str("content", "")
        if content == "":
            return webutil.FailedResult(message="内容不能为空")

        if task_id == 0:
            task = TodoRecord()
            task.user_id = user_id
            task.content = content
            task.priority = data.get_str("priority", TodoPriorityEnum.normal.value)
            task.project_id = project_id
            task.begin_time = parse_time_ms(data.get_str("begin_time", ""))
            task.end_time = parse_time_ms(data.get_str("end_time", ""))
            TodoDao.create(task)
        else:
            task = TodoDao.get_by_id(task_id, user_id=user_id)
            if task is None:
                return webutil.FailedResult(message="待办不存在")
            task.content = content
            task.priority = data.get_str("priority", task.priority)
            task.project_id = project_id
            task.begin_time = parse_time_ms(data.get_str("begin_time", ""))
            task.end_time = parse_time_ms(data.get_str("end_time", ""))
            TodoDao.update(task)
        return webutil.SuccessResult()

    def handle_finish(self):
        return self._do_status(TodoStatusEnum.done.value)

    def handle_start(self):
        return self._do_status(TodoStatusEnum.in_progress.value)

    def handle_reset(self):
        return self._do_status(TodoStatusEnum.not_started.value)

    def handle_cancel(self):
        return self._do_status(TodoStatusEnum.canceled.value)

    def _do_status(self, status: str):
        user_id = xauth.current_user_id()
        task_id = xutils.get_argument_int("task_id", 0)
        TodoDao.update_status(task_id, status, user_id=user_id)
        return webutil.SuccessResult()

    def handle_delete(self):
        user_id = xauth.current_user_id()
        task_id = xutils.get_argument_int("task_id", 0)
        TodoDao.delete(task_id, user_id=user_id)
        return webutil.SuccessResult()


class TodoIndexHandler:
    """/todo 分发：无 project_id 展示项目列表，否则展示该项目待办列表"""

    @xauth.login_required()
    def GET(self):
        return self._dispatch()

    @xauth.login_required()
    def POST(self):
        return self._dispatch()

    def _dispatch(self):
        model = xutils.get_argument_str("model", "")
        project_id = xutils.get_argument_str("project_id", "")
        if model == "task" or (model == "" and project_id != ""):
            return TaskListPlugin().GET()
        return ProjectListPlugin().GET()


def _build_task_info_tags(task: TodoRecord, project_name: str = "") -> Div:
    """待办详情的基础信息（标签展示）"""
    status_labels = _enum_label_map(TodoStatusEnum)
    priority_labels = _enum_label_map(TodoPriorityEnum)

    tag_box = Div(css_class="todo-detail-tags")
    tag_box.add(TextTag(text=status_labels.get(task.status, task.status),
                        css_class=STATUS_TAG_CLASS.get(task.status, "gray")))
    tag_box.add(TextTag(text=priority_labels.get(task.priority, task.priority),
                        css_class=PRIORITY_TAG_CLASS.get(task.priority, "gray")))
    tag_box.add(TextTag(text=project_name or T("未分类"), css_class="lightblue"))

    begin_time = format_time_ms(task.begin_time)
    if begin_time:
        tag_box.add(TextTag(text=T("开始 %s") % begin_time, css_class="lightgray"))
    end_time = format_time_ms(task.end_time)
    if end_time:
        tag_box.add(TextTag(text=T("结束 %s") % end_time, css_class="lightgray"))
    done_time = format_time_ms(task.done_time)
    if done_time:
        tag_box.add(TextTag(text=T("完成 %s") % done_time, css_class="lightgray"))
    create_time = format_time_ms(task.create_time)
    if create_time:
        tag_box.add(TextTag(text=T("创建 %s") % create_time, css_class="lightgray"))
    return tag_box


class TodoDetailHandler:
    """待办详情页（基础信息 + 评论）"""

    @xauth.login_required()
    def GET(self):
        user_id = xauth.current_user_id()
        task_id = xutils.get_argument_int("task_id", 0)
        task = TodoDao.get_by_id(task_id, user_id=user_id)
        if task is None:
            raise web.seeother("/todo")

        project = ProjectDao.get_by_id(task.project_id) if task.project_id else None
        project_name = project.name if project is not None else ""
        task_list_href = "/todo?project_id=%s" % task.project_id

        kw = Storage()
        kw.title = T("待办详情")
        kw.html_title = T("待办详情")
        kw.show_back_btn = True
        kw.parent_link = TextLink(text=project_name or T("待办"), href=task_list_href)
        kw.back_url = task_list_href
        kw.content_html = mark_text(task.content)
        kw.info_tags = _build_task_info_tags(task, project_name)
        # 评论组件（复用，type=todo_task + 独立 target_id 空间隔离）
        kw.file = Storage(id=to_comment_target_id(task_id))
        kw.comment_list_url = "/todo/comment/list"
        kw.comment_save_url = "/todo/comment/save"
        kw.comment_create_type = "todo_task"
        kw.comment_title = T("评论")
        kw.show_comment = True
        kw.show_comment_edit = True
        return xtemplate.render("todo/page/todo_detail.html", **kw)
