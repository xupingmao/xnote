# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2016/12/05
# @modified 2020/01/30 16:13:43
import os
import json
import web
import math
import inspect
import six
import xconfig
import xauth
import xutils
from tornado.template import Template, Loader
from xutils import dateutil, quote, u
from xutils import ConfigParser, Storage, tojson

TEMPLATE_DIR = xconfig.HANDLERS_DIR
NAMESPACE    = dict(
    format_date = dateutil.format_date,
    format_time = dateutil.format_time,
    quote       = quote
)

_lang_dict = dict()
_mobile_name_dict = dict()
_loader = None

def load_languages():
    """加载系统语言配置"""
    global _lang_dict

    _lang_dict.clear()
    dirname = xconfig.LANG_DIR
    for fname in os.listdir(dirname):
        name, ext = os.path.splitext(fname)
        if ext != ".properties":
            continue
        fpath   = os.path.join(dirname, fname)
        content = xutils.readfile(fpath)
        config  = xutils.parse_config_text(content, ret_type = 'dict')
        _lang_dict[name] = config


def T(text, lang = None):
    if lang is None:
        lang = web.ctx.get('_lang')
        if lang is None and hasattr(web.ctx, "env"):
            # 语言环境
            lang = web.cookies().get("lang", "zh")
            web.ctx._lang = lang
        if lang is None:
            lang = 'zh'

    mapping = _lang_dict.get(lang)
    if mapping is None:
        return text
    else:
        return mapping.get(text, text)

class XnoteLoader(Loader):
    """定制Template Loader"""
    
    def resolve_path_old(self, name, parent_path=None):
        if parent_path and not parent_path.startswith("<") and \
            not parent_path.startswith("/") and \
                not name.startswith("/"):
            current_path = os.path.join(self.root, parent_path)
            file_dir = os.path.dirname(os.path.abspath(current_path))
            relative_path = os.path.abspath(os.path.join(file_dir, name))
            if relative_path.startswith(self.root):
                name = relative_path[len(self.root) + 1:]
        return name

    def resolve_path(self, name, parent_path=None):
        """tornado中的Template._get_ancestors方法会把template的路径作为parent_path参数,
        但是Loader默认的方法处理绝对路径时，不处理相对路径,参考resolve_path_old
        由于判断绝对路径是通过`/`开头，这样造成windows系统和posix系统的处理结果不一致

        统一修改为`{% extends <abspath> %}` 和 `{% include <abspath> %}`, 继承和包含的模板路径强制为全局的，
        这样做的好处是一般全局母版的位置是不变的，移动模块不需要修改母版位置，这里的`全局`也并不是真的全局，
        而是寻找母版或者include模板时不进行路径转换
        """
        # 处理默认的模板，这里hack掉
        if name == "base":
            return xconfig.BASE_TEMPLATE
        return name

    def _create_template(self, name):
        if name.endswith(".str"):
            return Template(name, name = name, loader = self)
        path = os.path.join(self.root, name)
        with open(path, "rb") as f:
            template = Template(f.read(), name=name, loader=self)
            return template

    def init_template(self, name, text):
        self.templates[name] = Template(text, name=name, loader=self)

def set_loader_namespace(namespace):
    """ set basic namespace """
    _loader.namespace = namespace

def get_user_agent():
    if xconfig.IS_TEST:
        return ""
    return web.ctx.env.get("HTTP_USER_AGENT")

def get_user_config(user):
    if not xauth.has_login():
        return Storage()
    return xauth.get_user_config(user)

@xutils.cache(prefix="message.count", expire=360)
def get_message_count(user):
    if user is None:
        return 0
    try:
        return xutils.call("message.count", user, 0)
    except:
        # 数据库被锁
        xutils.print_exc()
        return 0

def pre_render(kw):
    """模板引擎预处理过程"""
    user_name           = xauth.current_name() or ""

    kw["math"]          = math
    kw["_is_admin"]     = xauth.is_admin()
    kw["_has_login"]    = xauth.has_login()
    kw["_user_name"]    = user_name
    kw["_user_agent"]   = get_user_agent()
    # 处理首页公告
    kw["_top_notice"]   = None
    # 用于渲染其他组件
    kw["_render"]       = render
    kw["Storage"]       = Storage
    kw["xutils"]        = xutils
    kw["xconfig"]       = xconfig
    kw["_user_config"]   = get_user_config(user_name)
    kw["_notice_count"] = get_message_count(user_name)
    kw["T"]             = T
    kw["HOME_PATH"]     = xconfig.get_user_config(user_name, "HOME_PATH")
    if hasattr(web.ctx, "env"):
        kw["HOST"] = web.ctx.env.get("HTTP_HOST")

    if len(xconfig.errors) > 0:
        kw["warn"] = "; ".join(xconfig.errors)

    # render input
    _input = web.ctx.get("_xnote.input")
    if _input is not None:
        kw.update(_input)

def post_render(kw):
    pass

def get_mobile_template(name):
    global _mobile_name_dict
    global TEMPLATE_DIR

    mobile_name = _mobile_name_dict.get(name)
    if mobile_name != None:
        return mobile_name

    if name.endswith(".html"):
        # 检查文件是否存在
        mobile_name = name[:-5] + ".mobile.html"
        fpath = os.path.join(TEMPLATE_DIR, mobile_name)
        if os.path.exists(fpath):
            _mobile_name_dict[name] = mobile_name
            return mobile_name
    _mobile_name_dict[name] = name
    return name

def is_mobile_device(user_agent):
    if user_agent is None:
        return False
    user_agent_lower = user_agent.lower()
    for name in ("iphone", "android"):
        if user_agent_lower.find(name) >= 0:
            return True
    return False

def render_by_ua(name, **kw):
    user_agent = get_user_agent()
    print(user_agent)
    if is_mobile_device(user_agent):
        # iPhone的兼容性不行，要用简化版页面，安卓暂时不用
        mobile_name = get_mobile_template(name)
        return render(mobile_name, **kw)
    return render(name, **kw)

@xutils.timeit(name = "Template.Render", logfile = True)
def render(template_name, **kw):
    nkw = {}
    pre_render(nkw)
    nkw.update(kw)
    post_render(nkw)

    if hasattr(web.ctx, "env"):
        # 不一定是WEB过来的请求
        _input = web.input()
        if _input.get("_format") == "json":
            web.header("Content-Type", "application/json")
            return tojson(nkw)
    return _loader.load(template_name).generate(**nkw)

def render_text(text, template_name = "<string>", **kw):
    """使用模板引擎渲染文本信息,使用缓存
    TODO 控制缓存大小，使用FIFO或者LRU淘汰
    """
    nkw = {}
    pre_render(nkw)
    nkw.update(kw)

    # 热加载模式下str的id会变化
    name = "template@%s.str" % hash(text)
    _loader.init_template(name, text)
    return _loader.load(name).generate(**nkw)

    
def get_code(name):
    return _loader.load(name).code


def get_templates():
    """获取所有模板的浅拷贝"""
    return _loader.templates.copy()

    
def reload():
    """reload template manager"""
    global _loader
    _loader = XnoteLoader(TEMPLATE_DIR, namespace = NAMESPACE)
    _loader.reset()
    load_languages()

def init():
    reload()

class Panel:

    def __init__(self):
        self.children = []

    def add(self, child):
        self.children.append(child)

    def render(self):
        html = '<div class="row x-plugin-panel">'
        for child in html:
            html += child.render()
        html += '</div>'
        return html

class Input:
    """输入文本框"""
    def __init__(self, label, name, value):
        self.label = label
        self.name = name
        self.value = value

    def render(self):
        html  = '<div class="x-plugin-input">'
        html +=   '<label class="x-plugin-input-label">%s</label>' % self.label
        html +=   '<input class="x-plugin-input-text" name="%s" value="%s">' % (self.name, self.value)
        html += '</div>'
        return html

class Textarea:

    def __init__(self, label, name, value):
        pass

class TabLink:
    """tab页链接"""
    def __init__(self):
        pass

class SubmitButton:
    """提交按钮"""

    def __init__(self, label):
        pass

class ActionButton:
    """查询后的操作行为按钮，比如删除、刷新等"""

    def __init__(self, label, action, context = None):
        pass

class ConfirmButton:
    """确认按钮"""

    def __init__(self, label, action, context = None):
        pass

class PromptButton:
    """询问输入按钮"""

    def __init__(self, label, action, context = None):
        pass

class DataTable:
    """数据表格"""

    def __init__(self, headings, data):
        """初始化数据表格
        @param {dict} headings 表头
        @param {dict} data 数据
        """
        pass

CATEGORY_NAME_DICT = dict(network = '网络', 
    file = '文件',
    dir  = '文件',
    note = '笔记',
    system = '系统'
)

class BasePlugin:
    """插件的基类"""

    # 插件的标题
    title = "PluginName"
    description = ""
    
    # 默认需要管理员权限访问
    require_admin = True
    # 要求的访问权限
    required_role = "admin"

    # 插件分类 {note, dir, system, network}
    category = None

    # 侧边栏自定义HTML
    aside_html = u("")
    show_aside = False

    # 搜索配置
    search_action = "/search"
    search_placeholder = None
    # 插件路径
    fpath = None

    # 输入框默认文案
    placeholder     = u("")
    editable        = True

    # 工具分为header、body、footer几个部分
    # * header展示输入面板
    # * body展示主数据（包括分页）
    # * footer 展示相关操作
    header = Panel()
    body   = Panel()
    footer = Panel()
    btn_text = T("处理")
    show_search = True
    
    def __init__(self):
        # 输入框的行数
        self.rows            = 20    
        # 提交请求的方法
        self.method          = "POST"
        self.output          = u("")
        self.html            = u("")
        self.css_style       = u("")
        self.show_pagenation = False
        self.page_url        = "?page="
        self.option_links    = []
        
    def add_option_link(name, url):
        self.option_links.append(dict(name=name, url = url))

    def write(self, text):
        self.output += u(text)

    def writeline(self, line):
        self.output += u(line + "\n")

    def writetext(self, text):
        self.output += u(text)

    def writehtml(self, html):
        self.html += u(html)

    def writetemplate(self, template, **kw):
        html = render_text(template, **kw)
        self.html += u(html.decode("utf-8"))

    def handle(self, input):
        raise NotImplementedError()

    def get_input(self):
        return xutils.get_argument("input", "")

    def get_format(self):
        """返回当前请求的数据格式"""
        return xutils.get_argument("_format", "")

    def get_page(self):
        """返回当前页码"""
        return xutils.get_argument("page", 1, type=int)

    def render(self):
        """图形界面入口"""
        if self.require_admin:
            xauth.check_login("admin")
        input  = self.get_input()
        error  = u("")
        output = u("")
        try:
            self.page = self.get_page()
            self.category_name = CATEGORY_NAME_DICT.get(self.category, '上级目录')
            output = self.handle(input) or u("")
            if self.get_format() == "text":
                web.header("Content-Type", "text/plain; charset:utf-8")
                return self.output + output

            # 复杂对象交给框架处理
            if isinstance(output, (dict, list)):
                return output

            # 处理侧边栏显示
            if self.aside_html != "" or len(self.option_links) > 0 or self.category:
                self.show_aside = True
        except web.webapi.Redirect:
            # 跳转的异常
            pass
        except:
            error = xutils.print_exc()
            web.ctx.status = "500 Internal Server Error"
        return render("plugins/base_plugin.html",
            model       = self,
            script_name = globals().get("script_name"),
            fpath       = self.fpath,
            description = self.description,
            error       = error,
            html_title  = self.title,
            title       = self.title,
            method      = self.method,
            rows        = self.rows,
            input       = input, 
            output      = self.output + output,
            css_style   = self.css_style,
            show_aside  = self.show_aside,
            show_search = self.show_search,
            html        = self.html,
            search_action = self.search_action,
            search_placeholder = self.search_placeholder)

    def on_action(self, name, context, input):
        """处理各种按钮行为，包括 action/confirm/prompt 等按钮
        @param {string} name 按钮名称
        @param {object} context 上下文，渲染的时候放入的
        @param {string/boolean} input 输入信息
        """
        pass

    def on_command(self, command):
        """命令行入口"""
        pass

    def on_install(self, context=None):
        """安装插件事件, TODO"""
        pass

    def on_uninstall(self, context=None):
        """卸载插件事件, TODO"""
        pass

    def on_init(self, context=None):
        """系统初始化事件"""
        pass

    def on_event(self, event):
        """其他事件"""
        pass

    def GET(self):
        return self.render()

    def POST(self):
        return self.render()

BaseTextPage   = BasePlugin
BaseTextPlugin = BasePlugin

