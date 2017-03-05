# encoding=utf-8
import web
import time
import os
import xutils
import logging
from logging.handlers import TimedRotatingFileHandler
import json
import threading
import sys
import re
import xtemplate

try:
    import psutil
except ImportError as e:
    psutil = None


class handler:

    interval = 30
    taskname = "monitor"

    # def __init__(self):
        # self.logger = logging.Logger(name="monitor")
        # handler = TimedRotatingFileHandler("log/monitor.log", when="d")
        # handler.setFormatter(logging.Formatter(fmt="%(asctime)s,%(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        # self.logger.addHandler(handler)

    def reload_logger(self):
        if self.logger is not None:
            self.logger.handlers[0].close()

        logger = logging.Logger(name="monitor")
        logger.setLevel(logging.INFO)
        fname = "log/monitor-%s.log" % (time.strftime("%Y-%m-%d"))
        handler = logging.FileHandler(fname)
        # 设置日志格式
        handler.setFormatter(logging.Formatter(fmt="%(asctime)s,%(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        # logger.handlers = [handler]
        # 原本有个StreamHandler在里面
        # print(logger.handlers)
        logger.handlers = [handler]
        self.logger = logger
        self.prev_fname = fname


    
    def GET(self):
        """
        You need catch exception by yourself
        """
        data = {}

        if psutil:
            percent_list = psutil.cpu_percent(interval=1, percpu=True)
            mem = psutil.virtual_memory()
            data["cpu"] = percent_list
            data["mem_used"] = mem.used
            data["mem_total"] = mem.total

            p = psutil.Process(pid=os.getpid())
            mem_info = p.memory_info()
            data["rss"] = mem_info.rss # Resident set size 进程占用的内存
            data["vms"] = mem_info.vms # 虚拟内存

            # windows下面CPU使用率始终是0，应该是获取不到
            data["cpu_percent"] = p.cpu_percent()

        elif xutils.is_windows():
            mem_usage = os.popen("tasklist /FI \"PID eq %s\" /FO csv" % os.getpid()).read()
            str_list = mem_usage.split("\n")
            data["task"] = str_list[1]
            
        data["time"] = xutils.format_time()
            
        log_file_name = time.strftime("log/monitor-%Y-%m-%d.log")
        with open(log_file_name, "a+") as fp:
            fp.write(json.dumps(data))
            fp.write("\n")
        return "OK"

        # self.logger.info(json.dumps(data))
        
        
        