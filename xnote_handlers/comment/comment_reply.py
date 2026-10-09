# -*- coding:utf-8 -*-
# @since 2026/10/08
# 评论回复相关接口（独立页面 / 列表片段 / AJAX 列表）
#
# 回复代码从 comment/__init__.py 拆分到本模块:
#   - CommentReplyPageHandler   : /comment/reply 回复独立页面(webui 组件构建,
#                                回复列表由 ListView 组件在服务端渲染, 不再依赖
#                                单独的列表接口/片段)
from urllib.parse import quote
from typing import List, Optional, TYPE_CHECKING

import xutils
from xnote.core import xauth
from xutils import webutil
from xutils import escape_html
from xutils import Storage
from xnote_handlers.comment import process_comments
from xnote_handlers.comment import dao_comment
from xnote_handlers.config import AsideConfig
from xnote.plugin import BasePluginV2
from xnote.webui import (Card, ListView, ListViewItem, TextContainer,
                         ActionBar, ActionButton,
                         RawHtml, TextLink, Textarea)

if TYPE_CHECKING:
    from xnote_handlers.comment.dao_comment import CommentVO
    from xnote.core.xauth import UserDO

class CommentReplyPageHandler(BasePluginV2):
    """回复页面（独立页面，替代原来的回复弹窗）

    通过 /comment/reply 打开, 用 webui 组件构建三个卡片:
      卡片1: 父评论信息
      卡片2: 回复列表(ListView 实现)
      卡片3: 回复输入框(Textarea) + 提交按钮(ActionButton)
    提交复用统一的 /comment/save 接口(返回 toast + 延迟 reload 命令, 整页刷新即看到新回复)。
    跳转进入时携带 redirect_url(来源页地址), 页面「返回」链接跳回。
    """

    show_category = False
    title = "评论回复"
    # 评论可匿名查看, 仅回复表单需要登录(由 /comment/save 校验)
    require_login = False
    require_admin = False

    def handle(self, input: str = "") -> None:
        self.update_aside(AsideConfig.default_aside_html)

        note_id: int = xutils.get_argument_int("note_id")
        parent_comment_id: int = xutils.get_argument_int("parent_comment_id")
        ref_comment_id: int = xutils.get_argument_int("ref_comment_id")
        ref_user_id: int = xutils.get_argument_int("ref_user_id")
        ref_user: str = xutils.get_argument_str("ref_user")
        redirect_url: str = xutils.get_argument_str("redirect_url")

        if note_id == 0 or parent_comment_id == 0:
            self.render_error("参数错误")
            return

        parent: Optional[CommentVO] = dao_comment.get_comment(parent_comment_id)
        if parent is None:
            self.render_error("评论不存在")
            return

        # 父评论与回复列表渲染前需补全 html / ref_user / ctime_str
        process_comments([parent], show_note=False)

        replies: "List[CommentVO]"
        total: int
        replies, total = dao_comment.list_replies(note_id, parent_comment_id, offset=0, limit=100)
        process_comments(replies, show_note=False)

        # 来源页作为「返回」链接(面包屑)
        if redirect_url:
            self.parent_link = TextLink(href=redirect_url, text="评论")

        # 卡片1: 父评论信息
        self.add_component(self._build_parent_card(parent))
        # 卡片2: 回复列表(ListView)
        self.add_component(self._build_reply_list_card(
            replies, note_id, parent_comment_id, redirect_url))
        # 卡片3: 回复输入框 + 提交按钮(仅登录后展示)
        if xauth.current_user() is not None:
            self.add_component(self._build_reply_form_card(
                note_id, parent_comment_id, ref_comment_id, ref_user_id))

    def _build_parent_card(self, parent: "CommentVO") -> Card:
        """卡片1: 展示被回复的父评论"""
        card = Card()
        action_bar = ActionBar(css_class="border-b")
        action_bar.add_title("原评论")
        card.add(action_bar)

        info = TextContainer(css_class="row px-2")
        info.add_span(parent.user, css_class="comment-user")
        info.add_span(parent.ctime_str, css_class="comment-time")
        card.add(info)

        if parent.ref_user:
            info.add_span(text=f"@{parent.ref_user}", css_class="comment-reply-at")
            
        if parent.html:
            info.add_br()
            info.add(RawHtml(parent.html))
        
        if parent.files:
            info.add_br()
            info.add(RawHtml(self._build_img_row(parent.files)))
        
        return card

    def _build_reply_list_card(self, replies: "List[CommentVO]", note_id: int,
                                parent_comment_id: int, redirect_url: str) -> Card:
        """卡片2: 回复列表, 采用 ListView 实现"""
        card = Card()
        action_bar = ActionBar(css_class="border-b")
        action_bar.add_title("回复列表")
        card.add(action_bar)


        list_view = ListView()
        user_info: Optional[UserDO] = xauth.current_user()
        user_id: int = user_info.id if user_info else 0
        current_url: str = webutil.get_request_url()

        for reply in replies:
            item = ListViewItem()
            item.add_span(reply.user, css_class="comment-user")
            item.add_span(reply.ctime_str, css_class="comment-time")
            if reply.ref_user:
                # ref_user 是纯文本, 用 add_span 而非 RawHtml; TextSpan 会自动 escape_html
                item.add_span("@" + reply.ref_user, css_class="comment-reply-at")
            if reply.html:
                item.add_br()
                item.add(RawHtml(reply.html))
            if reply.files:
                item.add(RawHtml(self._build_img_row(reply.files)))

            if user_id > 0:
                action_line = item.add_line()
                reply_url = f"/comment/reply?note_id={note_id}&parent_comment_id={parent_comment_id}&ref_comment_id={reply.id}&ref_user_id={reply.user_id}&ref_user={quote(reply.user)}&redirect_url={quote(redirect_url)}"
                action_line.add_link(text="回复", href=reply_url, css_class="btn btn-default")
                
                if reply.user_id == user_id:
                    action_line.add_nbsp()
                    action_line.add(ActionButton(
                        text="删除",
                        confirm_msg="确定删除回复吗",
                        css_class="btn danger",
                        data_names="*",
                        url="/comment/delete?comment_id=%s" % reply.id))
            list_view.add_item(item)

        card.add(list_view)
        return card

    def _build_reply_form_card(self, note_id: int, parent_comment_id: int,
                                ref_comment_id: int, ref_user_id: int) -> Card:
        """卡片3: 回复输入框(Textarea) + 提交按钮(ActionButton)"""
        card = Card()
        title_bar = ActionBar()
        title_bar.add_title("发表回复")
        card.add(title_bar)

        # name 必须页面唯一: ActionButton 的 data_names 通过 $("[name=reply_content]") 全局取值
        content: Textarea = Textarea(value="", name="reply_content",
                           placeholder="写下你的回复...",
                           css_class="no-outline comment-reply-textarea",
                           rows="4")
        card.add(content)

        # 复用统一的 /comment/save: data_names 抓取输入框内容, data_params 携带上下文 ID
        # (onclick 默认 xnote.plugin.onClick, 会先确认？否——无 confirm_msg 直接 post)
        btn = ActionButton(
            text="发送",
            type="button",
            url="/comment/save",
            data_names="reply_content",
            data_params={
                "note_id": note_id,
                "parent_comment_id": parent_comment_id,
                "ref_comment_id": ref_comment_id,
                "ref_user_id": ref_user_id,
            })
        card.add(btn)
        return card

    def _build_img_row(self, files: "List[str]") -> str:
        return "".join(
            '<img class="comment-img x-photo" alt="%s" src="%s?mode=thumbnail" data-src="%s">'
            % (escape_html(f), escape_html(f), escape_html(f)) for f in files)


xurls = (
    r"/comment/reply", CommentReplyPageHandler,
)
