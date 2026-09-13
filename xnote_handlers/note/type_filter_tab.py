# -*- coding: utf-8 -*-
"""笔记类型筛选 Tab（基于 TabBox 组件，替代 type_filter.html 的 tag 实现）

type_filter.html 原先用 `.tag` 徽章 + 一段 JS 设置 active，这里改用公共的
TabBox 组件，active 高亮由 x-tab.js 根据 URL 参数 `type`（或 tab_default
回退到 note_type）自动完成，与 message/todo 等页面的筛选保持一致。
"""
from typing import List

from xnote.plugin import TabBox
from xnote_handlers.note.models import NoteTypeInfo


def build(type_list, note_type="unknown"):
    # type: (List[NoteTypeInfo], str) -> TabBox
    """根据 type_list 与当前 note_type 构造笔记类型筛选 TabBox

    - tab_key="type" 与现有类型链接的 `?type=xxx` 参数保持一致
    - tab_default 回退到 note_type，兼容 URL 中不含 type 参数的页面（如 /note/dict）
    - 历史兼容：文档类型在 URL 中以 type=document 出现，但类型编码为 md
    """
    if note_type == "document":
        note_type = "md"

    tab = TabBox(tab_key="type", tab_default=note_type, css_class="btn-style card")
    for item in type_list:
        tab.add_item(title=item.name,
                     value=item.tag_code,
                     href=item.url,
                     css_class=item.css_class)
    return tab
