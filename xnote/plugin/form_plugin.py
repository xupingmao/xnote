# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2026-09-29 13:36:00
@LastEditors  : xupingmao
@LastEditTime : 2026-09-29 13:36:00
@FilePath     : /xnote/xnote/plugin/form_plugin.py
@Description  : 表单编辑插件基类，提供弹出/内联表单编辑的基础功能
"""

import xutils

from xutils import jsonutil
from xutils import webutil
from xnote.webui.form import DataForm, FormRowType, FormRowDateType
from xnote.webui import Card
from xnote.plugin.utils import ParamDict

from .base import BasePluginV2


class BaseFormPlugin(BasePluginV2):
    """表单编辑插件基类

    封装「表单编辑」场景的通用骨架。子类只需实现少量钩子，就能得到一个可用的
    「查看/列表 -> 编辑表单 -> 保存/删除」的插件：

    - ``?action=edit``   ：返回表单片段（供弹窗或页面内联渲染）
    - ``?action=save``   ：提交保存（子类实现 :meth:`handle_save`）
    - ``?action=delete`` ：提交删除（子类实现 :meth:`handle_delete`）

    ``handle()`` 按 ``action`` 反射派发到 ``handle_<action>()``，未命中时交给
    :meth:`handle_page`（子类可重写以承载列表/详情视图；纯表单插件保持默认即可，
    默认直接渲染编辑表单）。

    典型用法::

        class MyFormPlugin(BaseFormPlugin):
            def handle_edit(self):
                form = self.create_form()
                form.add_heading("基础信息")
                form.add_row("标题", "title")
                form.add_row("内容", "content", type=FormRowType.textarea)
                return self.response_form(form=form)

            def handle_save(self):
                data = self.get_data_dict()
                # 持久化 data ...
                return webutil.SuccessResult(message="保存成功")

            def handle_delete(self):
                data_id = xutils.get_argument_int("data_id")
                # 删除 data_id ...
                return webutil.SuccessResult(message="删除成功")
    """

    # 增加引用，方便子类在模板/代码里直接引用
    FormRowType = FormRowType
    FormRowDateType = FormRowDateType

    # ------------------------------------------------------------------
    # 请求派发
    # ------------------------------------------------------------------
    def handle(self, input=""):
        """按 action 字段反射派发到 handle_<action>()，未命中则交给 handle_page()"""
        action = xutils.get_argument_str("action")
        method = getattr(self, "handle_" + action, None)
        if method is not None:
            return method()
        return self.handle_page()

    # ------------------------------------------------------------------
    # 表单构建
    # ------------------------------------------------------------------
    def create_form(self) -> DataForm:
        """创建表单实例，子类可重写以返回 QueryForm / PageEditForm 等子类"""
        return DataForm()
        
    def handle_edit(self):
        """构建编辑表单，子类应重写以添加真实字段。

        默认实现返回一个最小示例表单，便于快速预览表单渲染效果。
        """
        form = self.create_form()
        form.add_heading("基础信息")
        form.add_row("id", "id", css_class="hide")
        form.add_row("只读属性", "readonly_attr", value="test", readonly=True)

        row = form.add_row("类型", "type", type=FormRowType.select)
        row.add_option("类型1", "1")
        row.add_option("类型2", "2")

        form.add_row("标题", "title")
        form.add_row("日期", "date", type=FormRowType.date)
        form.add_row("内容", "content", type=FormRowType.textarea)

        form.add_heading("高级信息")
        form.add_row("备注信息")
        
        self.render_form(form)

    # ------------------------------------------------------------------
    # 提交处理
    # ------------------------------------------------------------------
    def handle_save(self):
        """保存钩子，子类必须实现（返回 webutil.SuccessResult / FailedResult）"""
        # data = self.get_data_dict()
        return webutil.FailedResult(code="500", message="Not Implemented")

    def handle_delete(self):
        """删除钩子，子类必须实现（返回 webutil.SuccessResult / FailedResult）"""
        # data_id = xutils.get_argument_int("data_id")
        return webutil.FailedResult(code="500", message="Not Implemented")

    def handle_page(self):
        """页面视图钩子（列表/详情等）。默认直接渲染编辑表单，
        纯表单插件（无列表）保持默认即可；带列表的插件请重写。"""
        return self.handle_edit()

    # ------------------------------------------------------------------
    # 参数读取与响应
    # ------------------------------------------------------------------
    def get_param_dict(self) -> ParamDict:
        """从请求参数 ``data``（JSON 字符串）解析为带类型方法的参数字典"""
        data = xutils.get_argument_str("data")
        data_dict = jsonutil.fromjson(data)
        return ParamDict(data_dict)

    get_data_dict = get_param_dict



__all__ = [
    "BaseFormPlugin",
]
