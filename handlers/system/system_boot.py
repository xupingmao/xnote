# -*- coding:utf-8 -*-
# @author mark
# @since 2022/04/03 20:20:57
# @modified 2022/04/03 22:17:05
# @filename system_boot.py

import webbrowser
import threading
import time
import xutils

from xnote.core import xmanager
from xnote.core import xconfig

if xconfig.WebConfig.ringtone:
    xutils.say("系统已经启动上线")


# 启动打开浏览器选项
if xconfig.WebConfig.open_browser:
    class OpenThread(threading.Thread):
        def run(self):
            time.sleep(2)
            webbrowser.open("http://localhost:%s/" % xconfig.PORT)

    thread = OpenThread()
    thread.start()

@xmanager.listen("sys.init")
def boot_onload(ctx):
    print(ctx)

