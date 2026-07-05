# encoding=utf-8
from xnote.plugin import TextLink
from xnote.plugin import TabBox
from ._aside_config import AsideConfig
from xnote.core.xtemplate import LOAD_TIME
from ._tab_config import TabConfig

class LinkConfig:
    app_index = TextLink(text="应用", href="/system/index")
    develop_index = TextLink(text="开发", href="/plugin_list?category=develop")
    plugin_index = TextLink(text="插件中心", href="/plugin_list")
    plugin_index_btn = TextLink(text="插件", href="/plugin_list", css_class="btn-default")
    system_plugin_index = TextLink(text="系统", href="/plugin_list?category=system")
    note_plugin_index = TextLink(text="笔记", href="/plugin_list?category=note")
    admin_plugin_index = TextLink(text="管理员", href="/plugin_list?category=admin")
    system_info = TextLink(text="系统信息", href="/system/info")
    module_list = TextLink(text="模块信息", href="/system/module_list")
    taglist = TextLink(text="标签列表", href="/note/taglist")
    tag_manage = TextLink(text="标签管理", href="/note/tag_manage")
    dict_list = TextLink(text="词典", href="/note/dict")
    message = TextLink(text="随手记", href="/message")
    admin_settings = TextLink(text="管理员设置", href="/system/settings?category=admin")
    system_sync = TextLink(text="集群管理", href="/system/sync")
    task_list = TextLink(text="待办任务", href="/message/task")
    customized_css = TextLink(text="自定义CSS", href="/code/edit?type=script&path=user.css")
    customized_js = TextLink(text="自定义JavaScript", href="/code/edit?type=script&path=user.js")
    create_note = TextLink(text="新建笔记", href="/note/create")
    calendar = TextLink(text="今天", href="/note/calendar")
    user_settings = TextLink(text="用户设置", href="/user/info")
    driver_info_sql = TextLink(text="数据库驱动", href="/system/db/driver_info?type=sql")
    driver_info_kv = TextLink(text="KV数据库驱动", href="/system/db/driver_info")

class ScriptConfig:
    
    admin_js = f"/_static/js/admin.js?ts={LOAD_TIME}"