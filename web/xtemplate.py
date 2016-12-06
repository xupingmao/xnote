
from .tornado.template import Template, Loader
_loader = Loader("model")

def render(template_name, **kw):
    return _loader.load(template_name).generate(**kw)
    