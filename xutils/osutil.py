# encoding=utf-8

import subprocess
import platform
import os
import re
import logging
import time
from xutils.base import print_exc
from xutils.config import UtilityConfig

"""os适配工具
"""

def system(cmd, cwd = None):
    p = subprocess.Popen(cmd, cwd=cwd, 
                                 shell=True, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
    # out = p.stdout.read()
    # err = p.stderr.read()
    # if PY2:
    #     encoding = sys.getfilesystemencoding()
    #     os.system(cmd.encode(encoding))
    # else:
    #     os.system(cmd)

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
        import comtypes.client as cc
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
