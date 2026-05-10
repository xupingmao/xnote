import xutils
from xutils import Storage
from xnote.core import xauth
from xnote.webui import TabBox, ActionLink
from .dao_template import MessageTemplateDao

def handle_template_tab(kw: Storage, default_content: str, template_type="log"):
    template_content = ""
    user_id = xauth.current_user_id()
    template_id = xutils.get_argument_int("template_id")
    template_list = MessageTemplateDao.list_by_user(user_id=user_id, template_type=template_type)
    template_tab = TabBox(tab_key = "template_id", tab_default="0", css_class="btn-style btn-line-height")
    if len(template_list) == 0:
        template_tab.add_item(title="默认", value="0")
    else:
        template_content = template_list[0].content
        template_tab.tab_default = str(template_list[0].template_id)

        for template in template_list:
            template_tab.add_item(title=template.name, value=str(template.template_id))
            if template.template_id == template_id:
                template_content = template.content
                template_tab.tab_default = str(template_list[0].template_id)
    
    edit_link = ActionLink(text="编辑模板", href=f"/message/template?template_type={template_type}", css_class="bold")
    template_tab.extra.add(edit_link)
    
    kw.message_template_tab = template_tab
    kw.template_type = template_type
    
    if default_content == "":
        kw.default_content = template_content
        