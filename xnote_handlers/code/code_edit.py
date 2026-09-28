# -*- coding:utf-8 -*-
# Created by xupingmao on 2016/??/??
# @modified 2021/05/01 13:41:51

"""显示代码原文"""
import os
import web
import logging
import xutils

from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xconfig
from xnote.core import xmanager
from xnote.core import xnote_event
from xutils import Storage, fsutil
from xutils import textutil
from xutils import webutil
from xutils import netutil
from xnote.plugin import TextLink
from xnote.service.system_meta_service import SystemMetaEnum
from xnote_handlers.config import LinkConfig
from xnote.core.xnote_user_config import UserConfig, UserConfigItem
from xnote_handlers.config import LinkConfig

def can_preview(path: str):
    name, ext = os.path.splitext(path)
    return ext.lower() in (".md", ".csv")


def handle_embed(kw):
    """处理嵌入式常见"""
    embed = xutils.get_argument_bool("embed")

    kw.show_aside = False
    kw.embed = embed
    if embed:
        kw.show_aside = False
        kw.show_left = False
        kw.show_menu = False
        kw.show_search = False
        kw.show_path = False
        kw.show_nav = False


def handle_args(kw: Storage):
    show_path = xutils.get_argument_bool("show_path", True)
    kw.show_path = show_path


def resolve_path(path: str, type=''):
    is_b64 = xutils.get_argument_bool("b64")
    if is_b64:
        path = textutil.decode_base64(path)

    if type == "script":
        path = os.path.join(xconfig.SCRIPTS_DIR, path)
    path = os.path.abspath(path)
    if is_b64:
        return path
    return xutils.get_real_path(path)


class ViewSourceHandler:

    def get_default_kw(self):
        kw = Storage()
        kw._show_footer = False
        return kw

    @xauth.login_required("admin")
    def GET(self, path=""):
        template_name = "code/page/code_edit.html"
        path = xutils.get_argument_str("path", "")
        type = xutils.get_argument_str("type", "")
        offset = xutils.get_argument_int("offset")
        embed = xutils.get_argument_bool("embed")
        readonly = False

        kw = self.get_default_kw()
        # 处理嵌入页面
        handle_embed(kw)
        # 处理参数
        handle_args(kw)

        if path == "":
            return xtemplate.render(template_name,
                                    content="",
                                    error="path is empty")

        path = resolve_path(path, type)
        kw.path = path

        if not os.path.exists(path):
            kw = Storage()
            kw.content = ""
            kw.warn = "文件不存在"
            return xtemplate.render(template_name, **kw)

        error = ""
        warn = ""
        file_too_large = False
        part_links = []

        try:
            encoding = fsutil.detect_encoding(path, default_encoding="utf-8")
            assert isinstance(encoding, str)
            
            max_file_size = xconfig.MAX_TEXT_SIZE
            file_str_len = self.get_file_str_len(path, encoding)
            if file_str_len >= max_file_size:
                readonly = True
                file_too_large = True

            if file_too_large:
                part_links = self.build_part_links(file_str_len, max_file_size, offset)
            
            content = self.read_part(path, offset, max_file_size, encoding)

            plugin_name = fsutil.get_relative_path(path, xconfig.PLUGINS_DIR)
            # 使用JavaScript来处理搜索关键字高亮问题
            # if key != "":
            #     content = xutils.html_escape(content)
            #     key     = xhtml_escape(key)
            #     content = textutil.replace(content, key, htmlutil.span("?", "search-key"), ignore_case=True, use_template=True)
            show_preview = can_preview(path)
            
            if show_preview:
                quoted_path = xutils.quote(path)
                kw.right_link = TextLink(text="预览", href=f"/code/wiki/{quoted_path}?embed={embed}")
            
            kw.show_preview = show_preview
            kw.readonly = readonly
            kw.error = error
            kw.warn = warn
            kw.pathlist = xutils.splitpath(path)
            kw.name = os.path.basename(path)
            kw.content = content
            kw.plugin_name = plugin_name
            # 真实文件才支持删除, config/user_config 这类虚拟文件不支持
            kw.show_delete = os.path.isfile(path)
            # 删除之后回到父目录的文件浏览页, 编码方式对齐 FileItem.encoded_path
            parent_dir = os.path.dirname(path).replace("\\", "/")
            kw.parent_dir_url = "/fs/~" + xutils.encode_uri_component(parent_dir)
            kw.lines = content.count("\n")+1
            kw.file_too_large = file_too_large
            kw.part_links = part_links
            return xtemplate.render(template_name, **kw)
        except Exception as e:
            xutils.print_exc()
            error = e
        
        # 异常逻辑
        kw.name = ""
        kw.readonly = readonly
        kw.error = error
        kw.lines = 0
        kw.content = ""
        return xtemplate.render(template_name, **kw)
    
    def build_part_links(self, file_size: int, max_file_size: int, request_offset: int):
        part_links = []
        offset = 0
        webpath = webutil.get_request_url()
        index = 1
        while offset < file_size:
            href = webutil.replace_url_param(webpath, "offset", str(offset))
            css_class = ""
            if offset == request_offset:
                css_class = "red"
            part_links.append(TextLink(text=f"[{index}]", href=href, css_class=css_class))
            index += 1
            offset += max_file_size
        return part_links

    def read_part(self, path: str, offset: int, max_file_size: int, encoding: str):
        if offset < 0:
            offset = 0
        
        seek_size = offset
        buf_size = 1024*100 # 100K
        with open(path, "r+", encoding=encoding) as fp:
            while seek_size > 0:
                buf = fp.read(buf_size)
                if not buf:
                    break
                seek_size -= len(buf)
            return fp.read(max_file_size)
        
    def get_file_str_len(self, fpath: str, encoding: str):
        str_len = 0
        buf_size = 1024*100 # 100K
        with open(fpath, "r+", encoding=encoding) as fp:
            while True:
                buf = fp.read(buf_size)
                if not buf:
                    break
                str_len += len(buf)
        return str_len

class UpdateHandler(object):

    @xauth.login_required("admin")
    def POST(self):
        path = xutils.get_argument_str("path", "")
        content = xutils.get_argument_str("content", "")
        user_name = xauth.current_name_str()

        if content == "" or path == "":
            # raise web.seeother("/fs/")
            return webutil.FailedResult(code="400", message="path不能为空")
        else:
            content = content.replace("\r\n", "\n")
            xutils.savetofile(path, content)

            event = xnote_event.FileUploadEvent()
            event.fpath = path
            event.user_name = user_name
            event.user_id = xauth.current_user_id()

            # 发送通知刷新文件索引
            event.fire()
            # raise web.seeother("/code/edit?path=" + xutils.quote(path))
            return webutil.SuccessResult()


class EditConfigHandler:
    @xauth.admin_required()
    def GET(self):
        config_key = xutils.get_argument_str("config_key")
        sys_info = SystemMetaEnum.get_by_meta_key(meta_key=config_key)
        kw = Storage()
        kw.path = "init.py"
        kw.content = ""
        kw.post_action = "/code/edit/config"
        kw.show_fs_path = False
        kw.show_rename = False
        kw.parent_link = LinkConfig.admin_settings
        kw.code_type = "python"

        if sys_info is None:
            error = f"config not exists, config_key={config_key}"
            kw.error = error
        else:
            sys_info.expire_cache()
            kw.title = sys_info.meta_name
            kw.content = sys_info.value

        return xtemplate.render("code/page/code_edit.html", **kw)


    @xauth.admin_required()
    def POST(self):
        config_key = xutils.get_argument_str("config_key")
        content = xutils.get_argument_str("content")

        sys_info = SystemMetaEnum.get_by_meta_key(meta_key=config_key)
        if sys_info is None:
            return webutil.FailedResult("404", message="config_key not exists")
        
        sys_info.save_meta(content)
        return webutil.SuccessResult()


class EditUserConfigHandler:
    @xauth.login_required()
    def GET(self):
        config_key = xutils.get_argument_str("config_key")
        is_iframe = xutils.get_argument_bool("is_iframe")
        user_config = UserConfig.get_by_config_key(config_key=config_key)
        kw = Storage()
        kw.path = "config.md"
        kw.content = ""
        kw.post_action = "/code/edit/user_config"
        kw.show_fs_path = False
        kw.show_rename = False
        kw.code_type = "md"
        kw.is_iframe = is_iframe
        user_id = xauth.current_user_id()
        
        if is_iframe:
            kw.show_nav = False
            kw.show_search = False
            kw.show_title = False

        if user_config is None:
            error = f"config not exists, config_key={config_key}"
            kw.error = error
        else:
            user_config.expire_cache(user_id=user_id)
            kw.title = user_config.label
            kw.content = user_config.get_str(user_id=user_id)
            kw.help_text = user_config.help_text

        return xtemplate.render("code/page/code_edit.html", **kw)


    @xauth.admin_required()
    def POST(self):
        config_key = xutils.get_argument_str("config_key")
        content = xutils.get_argument_str("content")

        user_config = UserConfig.get_by_config_key(config_key=config_key)
        if user_config is None:
            return webutil.FailedResult("404", message="config_key not exists")
        user_id = xauth.current_user_id()
        user_config.save_config(user_id, content)
        return webutil.SuccessResult()

xurls = (
    r"/code/view_source", ViewSourceHandler,
    r"/code/view_source/update", UpdateHandler,
    r"/code/update", UpdateHandler,
    r"/code/edit", ViewSourceHandler,
    r"/code/edit/config", EditConfigHandler,
    r"/code/edit/user_config", EditUserConfigHandler,
)
