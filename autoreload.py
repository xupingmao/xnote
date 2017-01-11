from threading import Thread
import time
import subprocess
import sys
import types
import os
import sys
import traceback


_has_execv = sys.platform != 'win32'

_watched_files = []

_reload_trys = []

_callbacks = []

_reload_attempt = False

def print_exception(e):
    ex_type, ex, tb = sys.exc_info()
    print(ex)
    traceback.print_tb(tb)
    

def force_reload():
    _reload_attempt = True

class ReloadError(Exception):
    pass

class AutoReloadThread(Thread):

    def __init__(self, *callbacks):
        global _callbacks
        Thread.__init__(self)
        self.setDaemon(True)
        self.interval = 0.5
        self.watch_dirs = []

        for callback in callbacks:
            _callbacks.append(callback)

    def watch_dir(self, dir):
        self.watch_dirs.append(dir)
        _check_watch_dirs(self.watch_dirs)

    def watch_recursive_dir(self, dir):
        for root, dirs, files in os.walk(dir):
            for filename in files:
                abspath = os.path.join(root, filename)
                if abspath not in _watched_files:
                    _watched_files.append(abspath)

    def clear_watched_files(self):
        global _watched_files
        _watched_files = []

    def run(self):
        global _reload_attempt

        modify_times = {}
        while True:
            try:
                _reload_on_update(modify_times)
            except ReloadError as e:
                modify_times = {}
                for fn in _callbacks:
                    fn()
            time.sleep(self.interval)
            # this is not stable

def _check_watch_dirs(watch_dirs):
    for dir in watch_dirs:
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
        print("file %s modified, reload" % path)
        raise ReloadError()

def reload():
    for fn in _callbacks:
        fn()

def _reload():
    # sys.path fixes: see comments at top of file.  If sys.path[0] is an empty
    # string, we were (probably) invoked with -m and the effective path
    # is about to change on re-exec.  Add the current directory to $PYTHONPATH
    # to ensure that the new process sees the same path we did.
    path_prefix = '.' + os.pathsep
    if (sys.path[0] == '' and
            not os.environ.get("PYTHONPATH", "").startswith(path_prefix)):
        os.environ["PYTHONPATH"] = (path_prefix +
                                    os.environ.get("PYTHONPATH", ""))
    # call stop hooks
    for fn in _callbacks:
        fn()

    # return, just call the callbacks
    force_reload()
    return

    if not _has_execv:

        subprocess.Popen([sys.executable] + sys.argv)
        # os.popen(sys.executable + " " + " ".join(sys.argv))
        print("restart server")
        sys.exit(0)
    else:
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except OSError:
            # Mac OS X versions prior to 10.6 do not support execv in
            # a process that contains multiple threads.  Instead of
            # re-executing in the current process, start a new one
            # and cause the current process to exit.  This isn't
            # ideal since the new process is detached from the parent
            # terminal and thus cannot easily be killed with ctrl-C,
            # but it's better than not being able to autoreload at
            # all.
            # Unfortunately the errno returned in this case does not
            # appear to be consistent, so we can't easily check for
            # this error specifically.
            os.spawnv(os.P_NOWAIT, sys.executable,
                      [sys.executable] + sys.argv)
            # At this point the IOLoop has been closed and finally
            # blocks will experience errors if we allow the stack to
            # unwind, so just exit uncleanly.
            os._exit(0)
