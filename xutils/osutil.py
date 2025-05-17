# encoding=utf-8

import subprocess
import platform
import os
import re
import logging
import time
from xutils.base import print_exc
from xutils.config import UtilityConfig
from xutils import six
from os import system

"""os适配工具
"""


# 关于Py2的getstatusoutput，实际上是对os.popen的封装
# 而Py3中的getstatusoutput则是对subprocess.Popen的封装
# Py2的getstatusoutput, 注意原来的windows下不能正确运行，但是下面改进版的可以运行

def py2_getstatusoutput(cmd):
    """Return (status, output) of executing cmd in a shell."""
    import os
    # old
    # pipe = os.popen('{ ' + cmd + '; } 2>&1', 'r')
    # 这样修改有一个缺点就是执行多个命令的时候只能获取最后一个命令的输出
    pipe = os.popen(cmd + ' 2>&1', 'r')
    text = pipe.read()
    sts = pipe.close()
    if sts is None: sts = 0
    if text[-1:] == '\n': text = text[:-1]
    return sts, text

if six.PY2:
    getstatusoutput = py2_getstatusoutput
else:
    getstatusoutput = subprocess.getstatusoutput

def is_windows():
    return os.name == "nt"

def is_mac():
    return platform.system() == "Darwin"

def is_linux():
    return os.name == "linux"

def mac_say(msg):
    def escape(str):
        new_str_list = ['"']
        for c in str:
            if c != '"':
                new_str_list.append(c)
            else:
                new_str_list.append('\\"')
        new_str_list.append('"')
        return ''.join(new_str_list)

    msglist = re.split(r"[,.;?!():，。？！；：\n\"'<>《》\[\]]", msg)
    for m in msglist:
        m = m.strip()
        if m == "":
            continue
        cmd = "say %s" % escape(m)
        logging.info("MacSay %s", cmd)
        os.system(cmd.encode("utf-8"))

def windows_say(msg):
    try:
        import comtypes.client as cc # type: ignore
        # dynamic=True不生成静态的Python代码
        voice = cc.CreateObject("SAPI.SpVoice", dynamic=True)
        voice.Speak(msg)
    except ImportError:
        logging.warning("没有安装comtypes")
    except:
        print_exc()

def say(msg):
    if UtilityConfig.is_test:
        return
    if is_windows():
        windows_say(msg)
    elif is_mac():
        mac_say(msg)
    else:
        # 防止调用语音API的程序没有正确处理循环
        time.sleep(0.5)


def is_command_exists(command):
    if is_windows():
        # TODO 怎么判断命令是否存在
        try:
            result = subprocess.Popen(f"{command} --help", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            returncode = result.poll()
            return returncode == 0
        except FileNotFoundError:
            return False
    else:
        result = subprocess.Popen(f"which {command}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        returncode = result.poll()
        return returncode == 0
