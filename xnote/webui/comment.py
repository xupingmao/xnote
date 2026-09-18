# -*- coding:utf-8 -*-
# @since 2026/09/18
# 评论功能组件（纯 UI）：供笔记、待办、清单等场景复用。
#
# 本模块不依赖 xnote_handlers, 只负责把调用方传入的配置项渲染成统一模板
# (comment/page/comment.html) 的 #comment-box 容器与创建表单。
# 评论列表不在服务端静态输出, 而是由前端初始化时通过独立的列表加载接口
# (xnote.comment.loadList) 异步拉取并填充 #comments; 编辑 / 删除 / 新增后由
# 后端返回 toast + 延迟 reload 命令, 整页刷新重新加载评论列表(页面其它随评论
# 变化的区域也能一并更新)。评论数据的查询 / 更新接口集中在 xnote_handlers/comment 模块。
import typing

from typing import Optional
from xnote.webui.base import BaseComponent
from xnote.core import xtemplate


def _to_text(html):
    """xtemplate.render 返回 bytes, 需要统一转成 str 供组件返回"""
    if isinstance(html, bytes):
        return html.decode("utf-8")
    return html


class CommentBox(BaseComponent):
    """可复用的评论组件, 供笔记/待办/清单等场景使用。

    通过 `{% render comment_box %}` 渲染(comment_box 由 handler 构造并挂到 kw)。
    组件本身不查询数据库, 只输出 #comment-box 容器与创建表单; 评论列表由前端
    在初始化时通过独立的列表加载接口(xnote.comment.loadList)异步拉取并填充
    #comments, 编辑 / 删除 / 新增后由后端返回 toast + 延迟 reload 命令整页刷新。
    """

    def __init__(self, target_id: int, list_type: str = "note_id",
                 list_date: str = "", show_note: bool = False, show_edit: bool = False,
                 title: str = "评论", create_type: str = "",
                 save_url: str = "/comment/save", list_url: str = "/comment/list",
                 placeholder: str = "请输入评论, 支持粘贴图片...",
                 empty_text: str = "暂无评论~", btn_text: str = "评论",
                 show_title: bool = True, show_create: bool = True,
                 source_class: str = "", comment_class: str = "",
                 comment_order: Optional[str] = None, comment_page: Optional[int] = None):
        self.target_id = target_id
        self.list_type = list_type
        self.list_date = list_date
        self.show_note = show_note
        self.show_edit = show_edit
        self.title = title
        self.create_type = create_type
        self.save_url = save_url
        self.list_url = list_url
        self.placeholder = placeholder
        self.empty_text = empty_text
        self.btn_text = btn_text
        self.show_title = show_title
        self.show_create = show_create
        self.source_class = source_class
        self.comment_class = comment_class
        self.comment_order = comment_order
        self.comment_page = comment_page

    def to_kw(self):
        kw = dict(
            target_id=self.target_id,
            comment_list_type=self.list_type,
            comment_list_date=self.list_date,
            show_comment_note=self.show_note,
            show_comment_edit=self.show_edit,
            comment_title=self.title,
            comment_create_type=self.create_type,
            comment_save_url=self.save_url,
            comment_list_url=self.list_url,
            comment_placeholder=self.placeholder,
            comment_empty_text=self.empty_text,
            comment_btn_text=self.btn_text,
            show_comment_title=self.show_title,
            show_comment_create=self.show_create,
            comment_source_class=self.source_class,
            comment_class=self.comment_class,
            comment_order=self.comment_order,
        )
        # comment_page 不传时由模板从请求参数读取(默认 1), 避免传 None 覆盖掉默认值
        if self.comment_page is not None:
            kw["comment_page"] = self.comment_page
        return kw

    def render(self):
        html = xtemplate.render("comment/page/comment.html", **self.to_kw())
        return _to_text(html)
