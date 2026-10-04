# -*- coding: utf-8 -*-
# 随手记编辑表单（基于 BaseFormPlugin 重写编辑/新建/保存/删除）
#
# 该模块从 message.py 拆分出来，集中管理随手记的编辑逻辑。
# 注意：本模块在 message.py 末尾（所有应用符号定义完成之后）被导入，
# 因此顶层可直接 from .message import 复用其模块级符号，不会形成循环导入。
#
# 交互说明：
# - 编辑/新建通过普通链接跳转到本页（?action=edit|create），不再弹窗；
# - 返回列表的地址（back_url）由后端构建：优先取 HTTP Referer（即列表页地址，
#   可完整保留搜索关键词等参数），缺失或不合法时回退到 /message?tag=<tag>；
#   该地址写入表单隐藏字段，保存/删除后前端据此跳回原列表。
import web
import xutils

from xutils import netutil, webutil
from xnote.core import xauth
from xnote.plugin import BaseFormPlugin
from xnote.webui import PageEditForm
from xnote.core import xtemplate

from . import dao as msg_dao
from .dao import MessageDao, MessageDO
from .message import (
    create_message,
    update_message_content,
    DeleteAjaxHandler,
    READONLY_TODO_TAGS,
    READONLY_TODO_HINT,
    DEFAULT_TAG,
)
from .message_utils import mark_text_v2, get_standard_tag_set, normalize_tags
from .message_tag import filter_tag_list, add_tags_to_content, split_content_tags
from xnote_handlers.message.message_utils import TagHelper, get_remote_ip
from xnote_handlers.config import AsideConfig, LinkConfig

class MessageFormPlugin(BaseFormPlugin):
    """随手记编辑表单（基于 BaseFormPlugin 重写编辑/新建/保存/删除）

    页面内编辑使用 ``PageEditForm``（保存 + 删除），提交走 ``?action=save``，
    删除走 ``?action=delete``，与框架下其它表单插件保持一致。
    """
    
    title = "随手记编辑"
    parent_link = LinkConfig.message
    require_login = True
    require_admin = False

    def _build_form(self, detail: MessageDO, is_create=False):
        form = PageEditForm()
        form.path = "/message/form"
        form.model_name = "message"

        redirect_url = xutils.get_argument_str("redirect_url")
        tags, content = split_content_tags(detail.content)
        
        int_id = getattr(detail, "int_id", 0)
        form.add_hidden_input("id", value=str(int_id) if not is_create else "0")
        form.add_hidden_input("redirect_url", value=redirect_url)
        
        form.add_row("tag", "tag", value=detail.tag, css_class="hide")
        form.add_date_input("时间", "date", value=detail.date)
        form.add_textarea("内容", "content", value=content)

        user_id = xauth.current_user_id()
        tag_info_list = msg_dao.MsgTagInfoDao.list(user_id=user_id, offset=0, limit=1000)
        tag_info_list = filter_tag_list(tag_info_list, only_standard=True)
        
        tag_select = form.add_select(title="标签", field="tags", multiple=True, value=tags, select2_tags=True)
        for item in tag_info_list:
            tag_select.add_option(title=item.name, value=item.name)
                
        files_value = ",".join(detail.files or [])
        form.add_image("附件", "files", value=files_value)

            
        # 返回列表的地址（后端基于 Referer/tag 构建，提交时带回，保存/删除后跳回原列表）

        if not is_create:
            # 编辑态显示删除按钮，删除后跳回列表
            form.delete_url = "/message/form?action=delete"
            form.delete_reload_href = redirect_url
        return form

    def handle_edit(self):
        self.update_aside(AsideConfig.message_aside_html)
        # ts = xtemplate.LOAD_TIME
        # self.load_script(f"/_static/js/message/message.js?ts={ts}")
        
        id = xutils.get_argument_int("id")

        user_id = xauth.current_user_id()
        detail = msg_dao.MessageDao.get_by_int_id(id, user_id=user_id)
        if detail is None:
            web.ctx.status = "404 Not Found"
            return "数据不存在"

        if detail.ref != None:
            detail = msg_dao.get_message_by_key(detail.ref, user_name=xauth.current_name_str())
            
        if detail is None:
            web.ctx.status = "404 Not Found"
            return "数据不存在"

        # 返回地址优先取列表页 Referer，保留搜索关键词等参数；缺失则按 tag 回退
        self.render_form(self._build_form(detail))

    def handle_create(self):
        keyword = xutils.get_argument_str("keyword")
        tag = xutils.get_argument_str("tag", DEFAULT_TAG)

        detail = msg_dao.MessageDO()
        detail.tag = tag
        detail.content = keyword
        detail.date = xutils.format_date()
        detail.files = []
        self.render_form(self._build_form(detail, is_create=True))

    def handle_save(self):
        param = self.get_param_dict()
        msg_id = param.get_int("id", 0)
        content = param.get_str("content", "")
        files_str = param.get_str("files", "")
        tags = param.get_list("tags")
        # 去重并保持顺序（前端上传组件偶发会将同一附件计数两次）
        files = [f for f in dict.fromkeys(files_str.split(",")) if f]
        date = param.get_str("date", "")
        redirect_url = param.get_str("redirect_url")
        user_name = xauth.get_current_name()
        user_id = xauth.current_user_id()
        ip = get_remote_ip()

        if content == "" and len(files) == 0:
            return webutil.FailedResult(code="fail", message="输入内容为空!")

        tag = "log"
        if msg_id == 0:
            message = create_message(user_name, tag, content, ip, files, date=date)
            return webutil.SuccessResult(data=message, redirect_url=redirect_url)

        msg = MessageDao.get_by_int_id(msg_id)
        if msg is not None and msg.tag in READONLY_TODO_TAGS:
            return webutil.FailedResult(message=READONLY_TODO_HINT)
        
        normalize_tags(tags)
        content = add_tags_to_content(content, tags)
        
        update_message_content(msg_id, user_id, content, files, date=date)
        return webutil.SuccessResult(data=dict(id=msg_id), redirect_url=redirect_url)

    def handle_delete(self):
        param = self.get_param_dict()
        int_id = param.get_int("id", 0)
        if int_id == 0:
            return webutil.FailedResult(message="id为空")
        msg = MessageDao.get_by_int_id(int_id)
        if msg is None:
            return webutil.FailedResult(message="数据不存在")
        return DeleteAjaxHandler().delete_msg(msg)

xurls = (
    r"/message/form", MessageFormPlugin,
)
