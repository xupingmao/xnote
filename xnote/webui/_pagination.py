# -*- coding:utf-8 -*-

import math
import urllib.parse
import web

from xnote.core import xtemplate
from xnote.webui.base import BaseComponent

class Pagination(BaseComponent):
    """分页组件"""

    _template = xtemplate.compile_template("""
{% if page_max >= 0 %}
    <div class="pagenation">
        <a class="x-page-link" href="{{page_url}}1">首页</a>

        {% if page <= 1 %}
            <a class="x-page-link disabled">上一页</a>
        {% else %}
            <a class="x-page-link" href="{{page_url}}{{page-1}}">上一页</a>
        {% end %}

        {% for j in range(max(1, page-2), page) %}
            <a class="x-page-link desktop-only-inline" href="{{page_url}}{{j}}">{{j}}</a>
        {% end %}

        <a class="x-page-link active" href="#">{{page}}</a>
        
        {% for j in range(page+1, int(min(page+3, page_max+1))) %}
            <a class="x-page-link desktop-only-inline" href="{{page_url}}{{j}}">{{j}}</a>
        {% end %}

        {% if page >= page_max %}
            <a class="x-page-link disabled">下一页</a>
        {% else %}
            <a class="x-page-link" href="{{page_url}}{{page+1}}">下一页</a>
        {% end %}

        <a class="x-page-link" href="{{page_url}}{{page_max}}">尾页</a>
        {% if page_total > 0 and not _is_mobile %}
            <span class="x-page-span">{{page_total}}条记录</span>
        {% end %}
    </div>
{% end %}
""", name="pagination")

    def __init__(self, **kw):
        """分页组件初始化

        参数:
            page (int): 当前页码，默认 1
            page_max (int): 最大页码，默认 0（自动计算）
            page_size (int): 每页条数，默认 20
            page_url (str): 分页链接模板，默认 "?page="
            page_total (int): 总条数，默认 0
            page_totalsize (int): 总条数（别名），优先级高于 page_total
            page_current (int): 当前页码（兼容旧版），默认与 page 相同

        使用方式:
            # 在模板中（推荐）
            {% from xnote.webui import Pagination %}
            {% render Pagination(**globals()) %}

            # 在 Python 中
            Pagination(page=1, page_max=10, page_url="?page=").render()
            Pagination(page=1, page_size=20, page_total=100, page_url="?page=").render()
        """
        self.page = kw.get("page", 1)
        self.page_max = kw.get("page_max", 0)
        self.page_size = kw.get("page_size", 20)
        self.page_url = kw.get("page_url", "")
        self.page_total = kw.get("page_total", 0)
        if "page_totalsize" in kw:
            self.page_total = kw["page_totalsize"]
        self.page_current = kw.get("page_current", self.page)

        if not self.page_url:
            self.page_url = self._build_page_url()

    def _build_page_url(self):
        """基于当前请求参数自动构造 page_url（不依赖外部传入）
        
        示例:
            query = ?name=test&age=20       → ?name=test&age=20&page=
            query = ?name=test&age=20&page=3 → ?name=test&age=20&page=
        """
        query = web.ctx.get("query", "")
        if not query:
            return "?page="
        if query.startswith("?"):
            query = query[1:]
        params = urllib.parse.parse_qs(query, keep_blank_values=True)
        params.pop("page", None)
        if params:
            return "?" + urllib.parse.urlencode(params, doseq=True) + "&page="
        return "?page="

    def render(self):
        """渲染分页 HTML"""        
        page_max = self.page_max
        if page_max <= 0:
            if self.page_total <= 0:
                page_max = 1
            else:
                page_max = int(math.ceil(self.page_total / self.page_size))

        is_mobile = xtemplate.is_mobile_device()

        return self._template.generate(
            page=self.page,
            page_max=page_max,
            page_url=self.page_url,
            page_total=self.page_total,
            _is_mobile=is_mobile,
        )
