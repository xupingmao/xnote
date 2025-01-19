# encoding=utf-8

from xnote.core import xconfig
from xnote.core import xauth
from xutils.base import BaseEnum, EnumItem

class SettingTabEnumItem(EnumItem):

    def __init__(self, name="", value="", category="", need_admin=False):
        super().__init__(name, value)
        self.category = category
        self.need_admin = need_admin

    @property
    def url(self):
        return self.value
    
    def is_visible(self):
        if self.need_admin:
            return xauth.is_admin()
        return True

server_home = xconfig.WebConfig.server_home

class SettingTabEnum(BaseEnum):

    base = SettingTabEnumItem("基本设置", f"{server_home}/system/settings", category="base")
    user = SettingTabEnumItem("账号设置", f"{server_home}/user/info?category=user", category="user")
    search = SettingTabEnumItem("搜索设置", f"{server_home}/system/settings?category=search", category="search")
    admin = SettingTabEnumItem("管理员设置", f"{server_home}/system/settings?category=admin", category="admin", need_admin=True)
