from xnote.core import xtemplate


def get_default_sidebar_html():
    return xtemplate.render("common/sidebar/default.html")

def get_fs_sidebar_html():
    return xtemplate.render("fs/component/fs_sidebar.html")

def get_admin_sidebar_html():
    return xtemplate.render("system/component/admin_nav.html")