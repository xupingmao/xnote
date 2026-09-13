# -*- coding:utf-8 -*-
# @since 2026/09/13
# 全局默认搜索(综合搜索)纳入新待办模块的内容
import xutils
from xnote.core import xmanager, xconfig
from xnote.core.models import SearchContext, SearchResult
from xnote_handlers.todo.dao import TodoDao


@xmanager.searchable(".+", description="搜索待办")
def search_todo(ctx: SearchContext, expression=None):
    """综合搜索时一并检索新待办模块的内容，结果折叠为一条摘要（参考【随手记】）。

    该处理器经由 xmanager.fire("search", ctx) 触发，而 fire 仅在
    SearchHandler.do_search_default（category=default 的综合搜索）中执行，
    分类搜索(search_type=note/task/...)走 do_search_by_type 不会触发，
    因此仅影响【默认】搜索结果。
    """
    key = ctx.key
    if not key:
        return

    user_id = ctx.user_id
    if user_id == 0:
        return

    # 折叠展示：只给总数摘要，点击进入待办列表按关键词检索（与【随手记】一致）
    total = TodoDao.count_with_filters(user_id, key=key)
    if total == 0:
        return

    item = SearchResult()
    item.name = f"搜索到[{total}]个待办"
    item.url = xconfig.WebConfig.server_home + "/todo/task?model=task&key=" + xutils.quote(key) + "&status=all"
    item.icon = "fa fa-check-square-o"
    item.category = "task"
    item.show_more_link = True
    item.show_move = False
    ctx.tools.append(item)
