# -*- coding: utf-8 -*-
"""Switch 开关组件的渲染与取值测试"""
from . import test_base
from xnote.webui import Switch
from xnote.webui import DataForm

app = test_base.init()
BaseTestCase = test_base.BaseTestCase


def _to_str(html):
    if isinstance(html, bytes):
        return html.decode("utf-8")
    return html


class TestSwitch(BaseTestCase):

    def test_default_off(self):
        """默认关闭：无 active 类，隐藏域取 off_value"""
        html = _to_str(Switch(name="enabled", text="启用").render())
        assert 'name="enabled"' in html
        assert 'type="hidden"' in html
        assert 'value="false"' in html
        assert "active" not in html

    def test_checked(self):
        """默认开启：带 active 类，隐藏域取 on_value"""
        html = _to_str(Switch(name="enabled", text="启用", checked=True).render())
        assert "x-switch active" in html
        assert 'value="true"' in html

    def test_check_by_string_value(self):
        """直接把数据库里的字符串值传回 checked，便于编辑表单回填"""
        assert "x-switch active" in _to_str(Switch(name="f", checked="true").render())
        assert "x-switch active" in _to_str(Switch(name="f", checked="1").render())
        assert "active" not in _to_str(Switch(name="f", checked="false").render())
        assert "active" not in _to_str(Switch(name="f", checked="0").render())

    def test_custom_value(self):
        """自定义开/关的提交值"""
        html = _to_str(Switch(name="f", checked=True, on_value="1", off_value="0").render())
        assert 'value="1"' in html
        assert 'data-on-value="1"' in html
        assert 'data-off-value="0"' in html

        html = _to_str(Switch(name="f", checked=False, on_value="1", off_value="0").render())
        assert 'value="0"' in html

    def test_disabled(self):
        html = _to_str(Switch(name="f", text="禁用", disabled=True).render())
        assert "disabled" in html
        assert 'data-disabled="1"' in html

    def test_size(self):
        assert "switch-sm" in _to_str(Switch(name="f", size="sm").render())
        assert "switch-lg" in _to_str(Switch(name="f", size="lg").render())
        assert "switch-sm" not in _to_str(Switch(name="f").render())

    def test_text_escaped(self):
        """文本需要转义，避免 XSS"""
        html = _to_str(Switch(name="f", text="<script>").render())
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestFormSwitchRow(BaseTestCase):
    """DataForm 的开关行"""

    def test_add_switch(self):
        form = DataForm()
        form.add_switch(title="启用", field="enabled", checked=True)
        html = _to_str(form.render())
        assert 'name="enabled"' in html
        assert "x-switch active" in html

    def test_add_switch_unchecked(self):
        form = DataForm()
        form.add_switch(title="启用", field="enabled")
        html = _to_str(form.render())
        assert "x-switch" in html
        assert "active" not in html

    def test_readonly_switch_is_disabled(self):
        form = DataForm()
        form.add_switch(title="启用", field="enabled", readonly=True)
        html = _to_str(form.render())
        assert 'data-disabled="1"' in html
