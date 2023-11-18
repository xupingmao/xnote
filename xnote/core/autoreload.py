# encoding=utf-8
"""Xnote自动加载

autoreload会自动搜索指定目录下的文件
一旦修改时间发生变化会立即触发回调函数
"""

from threading import Thread
import time
import sys
import types
import os
import sys
import traceback
from xutils import dateutil

BLOCKED_EXT_LIST = [".pyc", ".class"]
_watched_files = []
_callbacks = []

def print_exception(e):
    ex_type, ex, tb = sys.exc_info()
    print(ex)
    traceback.print_tb(tb)

def log_info(fmt, *args):
    print(dateutil.format_time(), "[autoreload]", fmt.format(*args))

def force_reload():
    pass

class ReloadError(Exception):
    pass

class AutoReloadThread(Thread):

    def __init__(self, *callbacks):
        global _callbacks
        super(AutoReloadThread, self).__init__(name="AutoReloadThread")
        self.daemon = True
        self.interval = 0.5
        self.watched_dirs = []

        for callback in callbacks:
            _callbacks.append(callback)

    def watch_dir(self, dir, recursive=False):
        if recursive:
            self.watch_recursive_dir(dir)
            return
        self.watched_dirs.append(dir)
        _check_watch_dirs(self.watched_dirs)

    def watch_file(self, filepath):
        global _watched_files
        path = os.path.abspath(filepath)
        _watched_files.append(path)


    def watch_recursive_dir(self, dir):
        for root, dirs, files in os.walk(dir):
            for filename in files:
                abspath = os.path.join(root, filename)
                name, ext = os.path.splitext(filename)
                if ext in BLOCKED_EXT_LIST:
                    continue
                if abspath not in _watched_files:
                    _watched_files.append(abspath)

    def clear_watched_files(self):
        global _watched_files
        _watched_files = []

    def run(self):
        modify_times = {}
        while True:
            try:
                _reload_on_update(modify_times)
            except ReloadError as e:
                # 通过抛出一个ReloadError来通知重新加载
                modify_times = {}
                for callback in _callbacks:
                    callback()
            time.sleep(self.interval)


def _check_watch_dirs(watched_dirs):
    for dir in watched_dirs:
        _check_watch_dir(dir)

def _check_watch_dir(dir):
    global _watched_files
    for file in os.listdir(dir):
        path = os.path.join(dir, file)
        if path not in _watched_files:
            _watched_files.append(path)

def check_sys_modules(modify_times):
    for module in list(sys.modules.values()):
        # Some modules play games with sys.modules (e.g. email/__init__.py
        # in the standard library), and occasionally this can cause strange
        # failures in getattr.  Just ignore anything that's not an ordinary
        # module.
        if not isinstance(module, types.ModuleType):
            continue
        path = getattr(module, "__file__", None)
        if not path:
            continue
        if path.endswith(".pyc") or path.endswith(".pyo"):
            path = path[:-1]
        _check_file(modify_times, path)
    

def _reload_on_update(modify_times):
    for path in _watched_files:
        _check_file(modify_times, path)


def _check_file(modify_times, path):
    try:
        modified = os.stat(path).st_mtime
    except Exception as e:
        print_exception(e)
        if path in _watched_files:
            _watched_files.remove(path)
        return
    if path not in modify_times:
        modify_times[path] = modified
        return
    if modify_times[path] != modified:
        log_info("file {!r} modified, reload...", path)
        raise ReloadError()

def reload():
    for fn in _callbacks:
        fn()
