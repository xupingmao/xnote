# encoding=utf-8

from xnote.core import xauth
from xnote.core import xtemplate
from xutils import Storage
from xutils import dateutil

class PageVisitLogDO(Storage):
    def __init__(self, **kw):
        self.user_id = 0
        self.url = ""
        self.args = ""
        self.visit_cnt = 0
        self.visit_time = dateutil.format_datetime()
        self.update(kw)

def get_current_platform():
    return xtemplate.get_device_platform()

class PluginCategory:
    """插件分类"""
    required_roles = None
    icon_class = "fa fa-cube"

    def __init__(self, code, name, url=None, required_roles=None):
        self.code = code
        self.name = name
        self.required_roles = required_roles
        self.platforms = None
        self.css_class = ""
        if url is None:
            self.url = "/plugin_list?category=%s" % self.code
        else:
            self.url = url

    def is_visible(self):
        return self.is_visible_by_roles() and self.is_visible_by_platform()

    def is_visible_by_platform(self):
        if self.platforms is None:
            return True
        return get_current_platform() in self.platforms

    def is_visible_by_roles(self):
        if self.required_roles is None:
            return True
        return xauth.current_role() in self.required_roles

