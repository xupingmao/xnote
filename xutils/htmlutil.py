# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2017
# @modified 2018/09/22 01:17:06

def element(tag, text, clazz, attrs = None):
    """
        >>> element('span', '123', 'test')
        "<span class='test'>123</span>"
    """
    attrs_text = ''
    if attrs is not None:
        for attr in attrs:
            value = attrs[attr]
            attrs_text += ' %s=%s' % (attr, value)
    return "<%s class='%s' %s>%s</%s>" % (tag, clazz, attrs_text, text, tag)

def span(text, clazz = 'xnote-span'):
    return element("span", text, clazz)


def pre(text, clazz = 'xnote-pre'):
    """
        >>> pre('hello')
        "<pre class='xnote-pre'>hello</pre>"
    """
    return element("pre", text, clazz)

def div(text, clazz = 'xnote-div'):
    return element("div", text, clazz)

def link(name, link = None, clazz = "xnote-link"):
    if link is None:
        link = name
    return "<a class='%s' href='%s'>%s</a>" % (clazz, link, name)

def button(name, onclick=None, clazz='xnote-btn'):
    return element('button', name, clazz, dict(onclick=onclick))
