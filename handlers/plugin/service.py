# encoding=utf-8

import typing
from .models import PluginCategory

class CategoryService:

    category_list: typing.List[PluginCategory] = []

    @classmethod
    def define_plugin_category(cls, code: str,
                            name: str,
                            url=None,
                            raise_duplication=True,
                            required_roles=None,
                            platforms=None,
                            icon_class=None):
        for item in cls.category_list:
            if item.code == code:
                if raise_duplication:
                    raise Exception("code: %s is defined" % code)
                else:
                    return
            if item.name == name:
                if raise_duplication:
                    raise Exception("name: %s is defined" % name)
                else:
                    return
        category = PluginCategory(code, name, url, required_roles)
        category.platforms = platforms
        if icon_class != None:
            category.icon_class = icon_class
        cls.category_list.append(category)

    @classmethod
    def init_category_list(cls):    
        cls.define_plugin_category("all",      u"常用", icon_class="fa fa-th-large")
        cls.define_plugin_category("recent",   u"最近")
        cls.define_plugin_category("note",   u"笔记")
        cls.define_plugin_category("dir",      u"文件", required_roles=[
                   "admin"], icon_class="fa fa-folder")
        cls.define_plugin_category("system",   u"系统", required_roles=["admin"], platforms=[
                "desktop"],  icon_class="fa fa-gear")
        cls.define_plugin_category("network",  u"网络", required_roles=["admin"], platforms=[
                "desktop"], icon_class="icon-network-14px")
        cls.define_plugin_category("develop",  u"开发", required_roles=[
               "admin", "user"], platforms=["desktop"])
        cls.define_plugin_category("datetime", u"日期和时间", platforms=[],
           icon_class="fa fa-clock-o")
        cls.define_plugin_category("work",     u"工作", platforms=[
          "desktop"], icon_class="icon-work")
        cls.define_plugin_category("inner",    u"内置工具", platforms=[])
        cls.define_plugin_category("money",    u"理财", platforms=["desktop"])
        cls.define_plugin_category("test",     u"测试", platforms=[])
        cls.define_plugin_category("other",    u"其他", platforms=[])
        cls.define_plugin_category(
            "index",    u"全部分类", url="/plugin_category_list?category=index", icon_class="fa fa-th-large")

CategoryService.init_category_list()
