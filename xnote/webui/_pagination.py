# -*- coding:utf-8 -*-

import math
import typing

import web

from xnote.core import xtemplate
from xnote.webui.base import BaseComponent
from xutils.textutil import add_url_param, remove_url_param

DEFAULT_PAGE_ARG_NAME = "page"


def get_current_url() -> str:
    """获取当前页面的URL(包含query参数), 比如 /note/view?id=123

    非web环境(比如单元测试)返回空字符串
    """
    path = web.ctx.get("path", "")
    query = web.ctx.get("query", "")
    return "%s%s" % (path, query)


def _to_int(value: typing.Any, default_value: int) -> int:
    """分页相关参数统一转成int, 避免字符串参数参与算术运算报错"""
    if value is None or value == "":
        return default_value
    try:
        return int(value)
    except (TypeError, ValueError):
        return default_value


class Pagination(BaseComponent):
    """分页组件

    分页链接统一通过 add_url_param(page_url, page_arg_name, page_no) 生成,
    page_url 是基础URL(不含分页参数), 不设置时默认使用当前页面的URL。
    """

    _template = xtemplate.compile_template("""
{% if page_max >= 0 %}
    <div class="pagenation">
        <a class="x-page-link" href="{{add_url_param(page_url, page_arg_name, 1)}}">首页</a>

        {% if page <= 1 %}
            <a class="x-page-link disabled">上一页</a>
        {% else %}
            <a class="x-page-link" href="{{add_url_param(page_url, page_arg_name, page-1)}}">上一页</a>
        {% end %}

        {% for j in range(max(1, page-2), page) %}
            <a class="x-page-link desktop-only-inline" href="{{add_url_param(page_url, page_arg_name, j)}}">{{j}}</a>
        {% end %}

        <a class="x-page-link active" href="{{add_url_param(page_url, page_arg_name, page)}}">{{page}}</a>

        {% for j in range(page+1, int(min(page+3, page_max+1))) %}
            <a class="x-page-link desktop-only-inline" href="{{add_url_param(page_url, page_arg_name, j)}}">{{j}}</a>
        {% end %}

        {% if page >= page_max %}
            <a class="x-page-link disabled">下一页</a>
        {% else %}
            <a class="x-page-link" href="{{add_url_param(page_url, page_arg_name, page+1)}}">下一页</a>
        {% end %}

        <a class="x-page-link" href="{{add_url_param(page_url, page_arg_name, page_max)}}">尾页</a>
        {% if page_total > 0 and not _is_mobile %}
            <span class="x-page-span">{{page_total}}条记录</span>
        {% end %}
    </div>
{% end %}
""", name="pagination")

    def __init__(self, **kw):
        """分页组件初始化

        参数:
            page (int): 当前页码，默认 1（不传时取 page_current）
            page_max (int): 最大页码，默认 0（自动计算）
            page_size (int): 每页条数，默认 20
            page_url (str): 分页的基础URL(不含分页参数)，默认使用当前页面的URL
            page_arg_name (str): 分页参数的名称，默认 "page"
            page_total (int): 总条数，默认 0
            page_totalsize (int): 总条数（别名），优先级高于 page_total
            page_current (int): 当前页码（兼容旧版），默认与 page 相同

        使用方式:
            # 在模板中（推荐），page_url 等参数通过 kw 传入
            {% include common/pagination.html %}

            # 在 Python 中
            Pagination(page=1, page_max=10).render()
            Pagination(page=1, page_size=20, page_total=100, page_arg_name="comment_page").render()
        """
        page = kw.get("page")
        if page is None:
            page = kw.get("page_current", 1)

        self.page = _to_int(page, 1)
        self.page_max = _to_int(kw.get("page_max"), 0)
        self.page_size = _to_int(kw.get("page_size"), 20)
        self.page_arg_name = kw.get("page_arg_name") or DEFAULT_PAGE_ARG_NAME
        self.page_total = _to_int(kw.get("page_total"), 0)
        if "page_totalsize" in kw:
            self.page_total = _to_int(kw["page_totalsize"], 0)
        # 兼容旧版的 page_current
        self.page_current = _to_int(kw.get("page_current"), self.page)

        # page_url 是基础URL, 为空时取当前页面的URL, 并去掉已有的分页参数
        self.page_url = self._build_page_url(kw.get("page_url") or "")

    def _build_page_url(self, page_url: str) -> str:
        """构造分页的基础URL

        - page_url 为空时使用当前页面的URL
        - 去掉URL中已有的分页参数(兼容 `?page=` / `?type=x&page=` 这类旧写法)
        """
        if not page_url:
            page_url = get_current_url()
        return remove_url_param(page_url, self.page_arg_name)

    def build_page_url(self, page_no: typing.Any) -> str:
        """生成指定页码的URL"""
        return add_url_param(self.page_url, self.page_arg_name, str(page_no))

    def get_page_max(self) -> int:
        if self.page_max > 0:
            return self.page_max
        if self.page_total <= 0:
            return 1
        return int(math.ceil(self.page_total / self.page_size))

    def render(self):
        """渲染分页 HTML"""
        return self._template.generate(
            page=self.page,
            page_max=self.get_page_max(),
            page_url=self.page_url,
            page_arg_name=self.page_arg_name,
            page_total=self.page_total,
            add_url_param=add_url_param,
            _is_mobile=xtemplate.is_mobile_device(),
        )
