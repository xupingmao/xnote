# -*- coding: utf-8 -*-

import web
import time
import os
import xutils
import logging
from web import xtemplate

class task:
    __xinterval__ = 5
    __xtaskname__ = "test"

    def __init__(self):
        self.logger = None
        self.reload_logger()

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


    
    def __call__(self):
        """
        You need catch exception by yourself
        """
        fname = "log/monitor-%s.log" % (time.strftime("%Y-%m-%d"))
        if fname != self.prev_fname:
            self.reload_logger()

        if xutils.is_windows():
            mem_usage = os.popen("tasklist /FI \"PID eq %s\"" % os.getpid()).read()
            str_list = mem_usage.split("\n")
            self.logger.info(str_list[3])

class handler:

    def GET(self):
        pass


    def POST(self):
        pass

