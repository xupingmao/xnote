# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# @modified 2021/07/18 19:13:02

from xnote.core import xmanager
from xnote.core.xtemplate import T
from xnote.core.models import SearchContext
from .dict_dao import DictPublicDao, DictPersonalDao

# \u7ffb\u8bd1 翻译
# \u5b9a\u4e49 定义
@xmanager.searchable(r"(翻译|定义|define|def|translate)\s+([^\s]+)")
def do_translate(ctx: SearchContext):
    """模糊搜索"""
    search_key = ctx.groups[1]
    user_id = ctx.user_id
    results, _ = DictPublicDao.find_page(user_id=user_id, fuzzy_key=search_key, skip_count=True)
    for item in results:
        ctx.dicts.append(item.to_search_result())

@xmanager.searchable(r".+")
def on_default_search(ctx: SearchContext):
    """默认搜索的处理逻辑"""
    if not ctx.search_dict_strict:
        return

    user_id = ctx.user_id
    for dao in (DictPersonalDao, DictPublicDao):
        results, _ = dao.find_page(user_id=user_id, key=ctx.input_text, skip_count=True)
        for item in results:
            ctx.dicts.append(item.to_search_result())




