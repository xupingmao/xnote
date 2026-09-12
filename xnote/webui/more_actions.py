# -*- coding: utf-8 -*-
"""更多操作菜单组件

竖排3个点(⋮)按钮, 点击展开操作列表。适用于把一组操作按钮(置顶/重命名/删除等)
收纳进一个菜单, 保持界面简洁。菜单项通过 action_class 标记, 由调用方的 JS 委托处理。
"""

from typing import List, Optional

from xutils import escape_html

from .base import BaseComponent


class MenuItem:
    """菜单项"""

    def __init__(self, label: str, action_class: str = "",
                 session_id: int = 0, active: bool = False):
        self.label = label
        self.action_class = action_class
        self.session_id = session_id
        # 标记项是否处于激活态(如已置顶), 用于高亮
        self.active = active


class MoreActionsMenu(BaseComponent):
    """竖排3个点的"更多操作"菜单, 点击展开操作列表"""

    def __init__(self, items: Optional[List[MenuItem]] = None, toggle_icon: str = "⋮"):
        self.items: List[MenuItem] = items or []
        self.toggle_icon = toggle_icon

    def render(self):
        parts = ['<span class="x-more-menu">']
        parts.append('<span class="x-more-menu-toggle" title="更多">%s</span>'
                     % escape_html(self.toggle_icon))
        parts.append('<span class="x-more-menu-list">')
        for item in self.items:
            cls = "x-more-menu-item"
            if item.action_class:
                cls += " " + item.action_class
            if item.active:
                cls += " active"
            parts.append('<span class="%s" data-session-id="%s">%s</span>'
                         % (cls, item.session_id, escape_html(item.label)))
        parts.append('</span>')
        parts.append('</span>')
        return "".join(parts)
