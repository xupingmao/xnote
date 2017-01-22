# encoding=utf-8
import time
import xutils

class task:

    # 30秒检查一次
    interval = 30
    taskname = "time_reporter"

    def __call__(self):
        tm = time.localtime()
        if tm.tm_min % 10 != 0:
            return
        # 检查时间
        msg = "现在时间是%s时%s分" % (tm.tm_hour, tm.tm_min)
        output = xutils.getstatusoutput("call script\\speak.vbs %s" % msg)
        if output[0] != 0:
            print(output)