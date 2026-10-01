# encoding=utf-8
import sys
import time
import types
import unittest
from . import test_base
from xnote.core import xmanager
from xnote.core.xmanager import CronTaskManager
from xutils import Storage

app = test_base.init()

class TestMain(unittest.TestCase):

    def test_match(self):
        task_manager = CronTaskManager(None)

        tm = time.localtime()

        task = Storage()
        task.tm_wday = "*"
        task.tm_hour = "*"
        task.tm_min  = "*"
        r = task_manager.match(task, tm)
        self.assertEqual(True, r)

    def test_not_match(self):
        task_manager = CronTaskManager(None)

        tm = time.strptime("2017-01-01 10:10:00", "%Y-%m-%d %H:%M:%S")
        task = Storage()
        task.tm_wday = "*"
        task.tm_hour = "2"
        task.tm_min  = "*"
        r = task_manager.match(task, tm)
        self.assertEqual(False, r)

    def test_event_handler(self):
        ctx = Storage()
        xmanager.remove_event_handlers('test')
        
        @xmanager.listen("test", is_async = False)
        def my_handler(ctx):
            ctx.test = True
        
        xmanager.fire('test', ctx)
        self.assertEqual(True, ctx.test)

    def test_fix_module_name(self):
        """模块名归一化: 包目录下的 __init__.py 会被当成 pkg.__init__ 导入, 归一化后与包同名"""
        fix_module_name = xmanager.fix_module_name
        self.assertEqual("xnote_handlers.comment", fix_module_name("xnote_handlers.comment.__init__"))
        self.assertEqual("xnote_handlers.comment", fix_module_name("xnote_handlers.comment"))
        self.assertEqual("a.b", fix_module_name("a.b.__init__"))

    def test_handler_id_is_uuid(self):
        """未显式指定 id 时随机生成(uuid), 每次注册都是独立的实例ID"""
        handler1 = xmanager.EventHandler("test.uuid", lambda ctx: None, is_async=False)
        handler2 = xmanager.EventHandler("test.uuid", lambda ctx: None, is_async=False)
        self.assertTrue(handler1.id)
        self.assertNotEqual(handler1.id, handler2.id)

        handler3 = xmanager.EventHandler("test.uuid", lambda ctx: None, is_async=False, id="my-id")
        self.assertEqual("my-id", handler3.id)

    def test_handler_registered_once(self):
        """同一个处理器被注册多次(比如 pkg 和 pkg.__init__ 两个模块对象)时按标识幂等, 只保留一份"""
        event_type = "test.idem"
        xmanager.remove_event_handlers(event_type)

        pkg_mod = types.ModuleType("xnote_test_idem_pkg")
        init_mod = types.ModuleType("xnote_test_idem_pkg.__init__")
        sys.modules[pkg_mod.__name__] = pkg_mod
        sys.modules[init_mod.__name__] = init_mod
        code = "def on_idem(ctx):\n    ctx.count += 1\n"
        try:
            exec(compile(code, "<test>", "exec"), pkg_mod.__dict__)
            exec(compile(code, "<test>", "exec"), init_mod.__dict__)

            handler1 = xmanager.EventHandler(event_type, pkg_mod.on_idem, is_async=False)
            handler2 = xmanager.EventHandler(event_type, init_mod.on_idem, is_async=False)

            # `pkg.__init__` 和 `pkg` 归一化成同一个处理器标识
            self.assertEqual("xnote_test_idem_pkg.on_idem", handler1.func_name)
            self.assertEqual("xnote_test_idem_pkg.on_idem", handler2.func_name)
            self.assertEqual(handler1.key, handler2.key)

            mgr = xmanager.get_event_manager()
            mgr.add_handler(handler1)
            mgr.add_handler(handler2)
            self.assertEqual(1, len(mgr._handlers[event_type]))

            # 事件只触发一次
            ctx = Storage(count=0)
            xmanager.fire(event_type, ctx)
            self.assertEqual(1, ctx.count)
        finally:
            xmanager.remove_event_handlers(event_type)
            sys.modules.pop(pkg_mod.__name__, None)
            sys.modules.pop(init_mod.__name__, None)

    def test_handler_explicit_id(self):
        """显式指定相同 id 的处理器只保留一份(后注册的覆盖先注册的)"""
        event_type = "test.explicit_id"
        xmanager.remove_event_handlers(event_type)

        def on_a(ctx):
            ctx.a = True

        def on_b(ctx):
            ctx.b = True

        def on_c(ctx):
            ctx.c = True

        try:
            mgr = xmanager.get_event_manager()
            mgr.add_handler(xmanager.EventHandler(event_type, on_a, is_async=False, id="same-id"))
            mgr.add_handler(xmanager.EventHandler(event_type, on_b, is_async=False, id="same-id"))
            self.assertEqual(1, len(mgr._handlers[event_type]))
            self.assertEqual("on_b", mgr._handlers[event_type][0].func.__name__)

            # 未指定 id 的处理器之间彼此独立(随机id不会误合并), 按函数标识追加
            mgr.add_handler(xmanager.EventHandler(event_type, on_c, is_async=False))
            self.assertEqual(2, len(mgr._handlers[event_type]))
        finally:
            xmanager.remove_event_handlers(event_type)

    def test_handler_key_unique(self):
        """一次完整加载后, 同一个事件类型下处理器的标识(key)不重复"""
        handlers = xmanager.get_event_manager()._handlers.get("search", [])
        keys = [handler.key for handler in handlers]
        self.assertEqual(len(keys), len(set(keys)))
