# encoding=utf-8
import backup
import xtemplate
import web

html = """{% extends base.html %}

{% block body %}
    <p>路径 {{info.path}} </p>
    <p>备份时间 {{info.mtime}}</p>
    <p>大小 {{info.size}}</p>
    <p> <a href="/static/xnote.zip">下载</a>
    <p><a href="/system/backup_info?op=backup">重新备份</a></p>
{% end %}
"""


class handler:

    def GET(self):
        op = web.input(op=None).op
        if op == "backup":
            backup.zip_xnote()
        return xtemplate.render_text(html, info = backup.get_info())