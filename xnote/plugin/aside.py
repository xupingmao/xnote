from xnote.core import xtemplate

class AsideTemplate:

    @classmethod
    def get_default_aside_html(cls):
        return xtemplate.render("common/sidebar/default.html") 
    