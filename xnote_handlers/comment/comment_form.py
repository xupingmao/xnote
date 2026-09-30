# -*- coding: utf-8 -*-
# 评论编辑表单（基于 BaseFormPlugin 重写编辑/保存/删除）
#
# 参考 message/message_form.py。该模块从 comment/__init__.py 拆分出评论的编辑逻辑。
# 本模块通过文件底部的 xurls 自行注册路由（/comment/form），无需在 comment/__init__.py 再 import，
# xmanager 启动时会递归扫描 xnote_handlers/ 下所有 .py 并逐个读取模块自身的 xurls。
# 顶层可直接 from . import / from .dao_comment import 复用包内模块级符号（无循环导入风险）。
#
# 交互说明：
# - 编辑通过普通链接跳转到本页（?action=edit），不再弹窗；
# - 跳转时携带 redirect_url（当前列表/详情页地址），保存/删除后前端据此跳回原页。
import web
import datetime
import xutils

from xutils import webutil, dateutil
from xnote.core import xauth
from xnote.plugin import BaseFormPlugin, TextLink
from xnote.webui import PageEditForm

from . import dao_comment as comment_dao
from .dao_comment import get_comment, delete_comment, CommentDao
from . import COMMENT_TYPE, to_task_id


class CommentFormPlugin(BaseFormPlugin):
    """评论编辑表单（基于 BaseFormPlugin 重写编辑/保存/删除）

    页面内编辑使用 ``PageEditForm``（保存 + 删除），提交走 ``?action=save``，
    删除走 ``?action=delete``，与框架下其它表单插件保持一致。

    评论本身没有「新建」表单（新建走各业务页内联的评论框 /comment/save），
    所以这里只实现编辑/保存/删除。
    """

    title = "评论编辑"
    
    require_admin = False
    require_login = True

    def _build_form(self, comment, redirect_url=""):
        form = PageEditForm()
        form.path = "/comment/form"
        form.model_name = "comment"

        form.add_hidden_input("comment_id", value=str(comment.id))
        form.add_hidden_input("redirect_url", value=redirect_url)
        form.add_hidden_input("version", value=str(comment.version))

        form.add_textarea("内容", "content", value=comment.content)
        form.add_date_input("时间", "date", value=comment.date)

        files_value = ",".join(comment.files or [])
        form.add_image("附件", "files", value=files_value)

        # 编辑态显示删除按钮，删除后跳回原页
        form.delete_url = "/comment/form?action=delete"
        form.delete_reload_href = redirect_url
        return form

    def handle_edit(self):
        comment_id = xutils.get_argument_int("comment_id")
        redirect_url = xutils.get_argument_str("redirect_url")

        user_name = xauth.current_name()
        comment = get_comment(comment_id)
        if comment is None:
            web.ctx.status = "404 Not Found"
            return "评论不存在"
        if comment.user != user_name:
            web.ctx.status = "403 Forbidden"
            return "无操作权限"

        # 返回列表/详情页地址（前端从当前页带来），保存/删除后跳回原页
        if redirect_url:
            self.parent_link = TextLink(text="返回", href=redirect_url)
        self.render_form(self._build_form(comment, redirect_url=redirect_url))

    def handle_save(self):
        param = self.get_param_dict()
        comment_id = param.get_int("comment_id", 0)
        content = param.get_str("content", "")
        date = param.get_str("date", "")
        files_str = param.get_str("files", "")
        # 去重并保持顺序（前端上传组件偶发会将同一附件计数两次）
        files = [f for f in dict.fromkeys(files_str.split(",")) if f]
        version = param.get_int("version", 0)
        redirect_url = param.get_str("redirect_url")
        user_name = xauth.current_name()

        if content == "" and len(files) == 0:
            return webutil.FailedResult(code="fail", message="输入内容为空!")

        comment = get_comment(comment_id)
        if comment is None:
            return webutil.FailedResult(code="404", message="评论不存在")
        if comment.user != user_name:
            return webutil.FailedResult(code="403", message="无权限操作")

        # 修改时间：date 字段变动时重算 create_time（毫秒时间戳）
        update_ctime = False
        if date:
            old_datetime = datetime.datetime.fromtimestamp(comment.create_time / 1000)
            old_date_str = old_datetime.strftime("%Y-%m-%d")
            if date != old_date_str:
                new_datetime_str = f"{date} {old_datetime.strftime('%H:%M:%S')}"
                new_datetime = dateutil.parse_datetime(new_datetime_str)
                comment.create_time = int(new_datetime * 1000)
                update_ctime = True

        comment.content = content
        comment.files = files
        comment.version = version

        try:
            CommentDao.update(comment, update_ctime=update_ctime)
        except ValueError as e:
            return webutil.FailedResult(code="400", message=str(e))

        return webutil.SuccessResult(data=dict(id=comment_id), redirect_url=redirect_url)

    def handle_delete(self):
        param = self.get_param_dict()
        comment_id = param.get_int("comment_id", 0)
        redirect_url = param.get_str("redirect_url")
        user = xauth.current_name()

        comment = get_comment(comment_id)
        if comment is None:
            return webutil.SuccessResult()
        if user != comment.user:
            return webutil.FailedResult(message="unauthorized")

        # 用评论记录自身的 type 区分笔记/待办(不依赖 target_id 区间)。
        # 旧数据可能把笔记评论误标为 todo_task, 而对应待办并不存在(脏数据);
        # 此时不应阻断删除 —— 只要 user 一致(上面的校验已通过), 就允许删除, 仅跳过待办评论数回写。
        is_todo = comment.type == COMMENT_TYPE
        if is_todo:
            from xnote_handlers.todo.dao import TodoDao
            task = TodoDao.get_by_id(to_task_id(int(comment.note_id)),
                                     user_id=xauth.current_user_id())
            if task is None:
                # 待办不存在(脏数据 / 已删除): 不阻断, 按普通评论删除即可
                is_todo = False

        delete_comment(comment_id)

        if is_todo:
            target_id = int(comment.note_id)
            new_count = comment_dao.count_comment_by_note(target_id, type=COMMENT_TYPE)
            TodoDao.update_comment_count(to_task_id(target_id), new_count)

        return webutil.SuccessResult(redirect_url=redirect_url)


xurls = (
    r"/comment/form", CommentFormPlugin,
)
