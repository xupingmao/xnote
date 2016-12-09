'''
    Tornado template wrapper
    @since 2016/12/05
'''

from .tornado.template import Template, Loader

from util import dateutil

TEMPLATE_DIR = "model"
NAMESPACE    = dict(
    format_date = dateutil.format_date,
    format_time = dateutil.format_time
)    

_loader = Loader(TEMPLATE_DIR, namespace = NAMESPACE)
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

    
def get_code(name):
    return _loader.load(name).code
    
    
def reload():
    global _loader
    _loader = Loader(TEMPLATE_DIR, namespace = NAMESPACE)