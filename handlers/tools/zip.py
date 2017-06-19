# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/01
# 

"""压缩文件"""

import os
import xutils
import xtemplate

html = """
{% extends base.html %}

{% block body %}

<h2>压缩文件</h2>

<a href="/fs/{{dirname}}">返回目录</a>
<form method="POST">
<div class="col-md-12">
    <div>
        目录路径<textarea class="col-md-12" name="dirname">{{dirname}}</textarea>
    </div>
    <div>
        目标文件名<textarea class="col-md-12" name="destname">{{destname}}</textarea>
    </div>
    <button>压缩</button>
</div>
</form>

{% end %}
"""

class handler:

    def GET(self):
        dirname = xutils.get_argument("dirname", "")
        destname = xutils.get_argument("destname")
        if dirname != "":
            dirname  = os.path.abspath(dirname)
            basename = os.path.basename(dirname)
            destname = basename + ".zip"
        return xtemplate.render_text(html, dirname=dirname, destname=destname)

    def POST(self):
        dirname  = xutils.get_argument("dirname")
        destname = xutils.get_argument("destname")
        xutils.zip_dir(dirname, os.path.join(dirname, destname))
        return xtemplate.render_text(html, dirname=dirname, destname=destname)



