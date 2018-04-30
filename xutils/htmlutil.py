
def element(tag, text, clazz):
    """
    >>> element('span', '123', 'test')
    "<span class='test'>123</span>"
    """
    return "<%s class='%s'>%s</%s>" % (tag, clazz, text, tag)

def span(text, clazz = 'xnote-span'):
    return element("span", text, clazz)


def pre(text, clazz = 'xnote-pre'):
    return element("pre", text, clazz)

def div(text, clazz = 'xnote-div'):
    return element("div", text, clazz)

def link(link, name = None, clazz = "xnote-link"):
    if name is None:
        name = link
    return "<a class='%s' href='%s'>%s</a>" % (clazz, link, name)
