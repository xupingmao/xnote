'''
    Tornado template wrapper
    @since 2016/12/05
'''

from .tornado.template import Template, Loader
_loader = Loader("model")
_hooks = []

def set_loader_namespace(namespace):
    """ set basic namespace """
    _loader.namespace = namespace

def add_render_hook(hook):
    _hooks.append(hook)
    
def render(template_name, **kw):
    nkw = {}
    for hook in _hooks:
        hook(nkw)
    nkw.update(kw)
    return _loader.load(template_name).generate(**nkw)
    