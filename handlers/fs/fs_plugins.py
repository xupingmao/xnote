# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/03/22 22:57:39
# @modified 2020/03/21 17:29:30
import web
import os
import xconfig
import xutils
import xtemplate
import sys
import xauth
from xutils import ziputil, textutil

def get_display_name(name):
    name, ext = os.path.splitext(name)
    if name.startswith("fs-"):
        # 兼容历史数据
        return name[3:]
    else:
        return name

def filter_command(x):
    return x.endswith(".py")

def list_commands():
    scripts = sorted(filter(filter_command, os.listdir(xconfig.COMMANDS_DIR)))
    return scripts

def suggest_commands(name):
    name, ext = os.path.splitext(name)
    commands = list_commands()
    if name == "" or name == ".py":
        print("所有命令如下")
    else:
        print("命令`%s`无效，你可以尝试" % name)
    suggested_list = []
    for command in commands:
        if command.find(name) >= 0:
            suggested_list.append(command)
    if len(suggested_list) > 0:
        for command in suggested_list:
            print(command)
    else:
        for command in commands:
            print(command)

class PluginsHandler:

    @xauth.login_required("admin")
    def GET(self):
        show_menu = xutils.get_argument("show_menu", type=bool)
        embed = xutils.get_argument("embed", type=bool)
        path = xutils.get_argument("path")
        if path == "" or path == None:
            path = xconfig.DATA_DIR
        scripts = list_commands()

        show_search = True
        if embed:
            show_menu = False
            show_search = False

        return xtemplate.render("fs/page/fs_plugins.html", 
            show_aside = False,
            path = path, 
            scripts = scripts, 
            get_display_name = get_display_name,
            show_menu = show_menu,
            show_search = show_search)

class RunPluginHandler:

    @xauth.login_required("admin")
    def POST(self):
        func_ret = None
        sys.stdout.record()
        original_name = ""
        try:
            name = xutils.get_argument("name")
            path = xutils.get_argument("path")
            original_name = name
            confirmed = xutils.get_argument("confirmed") == "true"
            name, input = textutil.parse_simple_command(name)
            name = xconfig.get_alias(name, name)
            new_command = "%s %s" % (name, input)
            name, input = textutil.parse_simple_command(new_command)
            
            if not name.endswith(".py"):
                name += ".py"
            if input == "":
                input = xutils.get_argument("input", "")
            vars = dict()
            script_name = os.path.join("commands", name)
            script_path = os.path.join(xconfig.COMMANDS_DIR, name)
            if not os.path.exists(script_path):
                suggest_commands(name)
            else:
                xutils.load_script(script_name, vars = vars)
                main_func = vars.get("main", None)
                if main_func is not None:
                    real_path = xutils.get_real_path(path)
                    func_ret = main_func(path = real_path, confirmed = confirmed, input = input)
                else:
                    print("main(**kw)方法未定义")
        except Exception as e:
            xutils.print_exc()
        
        header = "执行 %s<hr>" % name
        # footer = "\n%s\n执行完毕，请确认下一步操作" % line
        footer = ''
        result = sys.stdout.pop_record()
        if xutils.get_doctype(result) == "html":
            html = header + result[6:]
        else:
            html = header + xutils.mark_text(result)
        html += '''<input id="inputText" class="col-md-12 hide" placeholder="请输入参数" value="">'''
        html += '''<div><button class="btn-danger" onclick="runPlugin('%s', true)">确认执行</button></div>''' % original_name
        return dict(code="success", data = html, name = name)


class DownloadHandler:

    @xauth.login_required("admin")
    def GET(self, name=""):
        bufsize = 1024 * 100
        dirname = os.path.join(xconfig.SCRIPTS_DIR, name)
        outpath = os.path.join(xconfig.TMP_DIR, name + ".zip")
        ziputil.zip_dir(dirname, outpath = outpath)
        web.header("Content-Disposition", "attachment; filename=%s.zip" % name)
        with open(outpath, "rb") as fp:
            buf = fp.read(bufsize)
            while buf:
                yield buf
                buf = fp.read(bufsize)

xurls = (
    r"/fs_api/plugins", PluginsHandler,
    r"/fs_plugins", PluginsHandler,
    r"/fs_api/run_plugin", RunPluginHandler,
    r"/fs_api/download/(.+)", DownloadHandler
)
