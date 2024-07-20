# encoding=utf-8

import xutils
from xutils import webutil
from xnote.core import xauth
from xnote.service import DatabaseLockService

class AdminTestHandler:

    @xauth.login_required("admin")
    def GET(self):
        type = xutils.get_argument_str("type")
        if type == "lock":
            return self.test_lock()
        return webutil.FailedResult(code="400", message=f"unknown type: {type}")
    
    def test_lock(self):
        with DatabaseLockService.lock(lock_key="lock_test"):
            print("test lock")
        return webutil.SuccessResult()


xurls = (
    r"/admin/test", AdminTestHandler,
)
