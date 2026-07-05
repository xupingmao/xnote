from xnote.core import xtemplate

class _AsideConfigImpl:
    """侧边栏配置，新增的统一使用 @property 装饰器, @classmethod 仅用于兼容"""
    
    @classmethod
    def get_default_aside_html(cls):
        return xtemplate.render("common/sidebar/default.html")
    
    @classmethod
    def get_fs_aside_html(cls):
        return xtemplate.render("fs/component/fs_sidebar.html")
    
    @classmethod
    def get_admin_aside_html(cls):
        return xtemplate.render("system/component/admin_nav.html")

    @classmethod
    def get_settings_aside_html(cls):
        return xtemplate.render("settings/page/settings_sidebar.html")
    
    @classmethod
    def get_note_aside_html(cls):
        return xtemplate.render("note/component/sidebar/group_list_sidebar.html")
    
    @property
    def default_aside_html(self):
        return xtemplate.render("common/sidebar/default.html")

    @property
    def fs_aside_html(self):
        return xtemplate.render("fs/component/fs_sidebar.html")

    @property
    def admin_aside_html(self):
        return xtemplate.render("system/component/admin_nav.html")

    @property
    def settings_aside_html(self):
        return xtemplate.render("settings/page/settings_sidebar.html")
    
    @property
    def note_aside_html(self):
        return xtemplate.render("note/component/sidebar/group_list_sidebar.html")

AsideConfig = _AsideConfigImpl()
