# encoding=utf-8

import xutils
from xutils import webutil
from xutils import Storage
from xnote.core import xtemplate
from xnote.service import DatabaseLockService, JobService, JobInfoDO, JobStatusEnum
from xnote.plugin.table_plugin import BaseTablePlugin
from xnote.plugin import DataTable, FormRowType, TableActionType
from handlers.message.dao import MessageDao
from handlers.message.message_utils import process_message
from handlers.message import message_tag

class RepairInfo(Storage):
    def __init__(self, code="", name="", content=""):
        super().__init__()
        self.code = code
        self.name = name
        self.content = content
        self.repair_url = f"?action=repair&code={self.code}"
        self.repair_msg = f"确认修复【{self.name}】吗?"

    def do_content(self):
        """更新修复内容"""
        pass

    def do_repair(self):
        """执行修复动作"""
        return webutil.SuccessResult(message="修复成功")

class RepairMsgTag(RepairInfo):
    def do_content(self):
        job_info = JobService.get_latest_job(job_type=self.code)
        if job_info != None:
            self.content = f"修复时间:{job_info.mtime},修复结果:{job_info.job_result}"
        else:
            self.content = "未进行修复"
    
    def do_repair(self):
        with DatabaseLockService.lock(lock_key="fix_msg_tag", timeout_seconds=60) as lock:
            job_info = JobInfoDO()
            job_info.job_type = self.code
            job_info.job_params = ""
            with JobService.run_with_job(job_info):
                count = 0
                for msg in MessageDao.iter_all():
                    process_message(msg)
                    MessageDao.update_user_tags(msg)
                    message_tag.update_tag_amount_by_msg(msg)
                    count += 1

                job_info.job_result = f"修复{count}条记录"

        return webutil.SuccessResult(message="修复成功")


class RepairHandler(BaseTablePlugin):

    title = "数据修复"
    show_aside = True
    show_right = True

    repair_rows = [
        RepairMsgTag(code="fix_msg_tag", name="待办/随手记索引"),
    ]

    def get_page_html(self):
        return self.TABLE_HTML

    def get_aside_html(self):
        return xtemplate.render_text("{% include system/component/admin_nav.html %}")

    def handle_page(self):
        table = DataTable()
        table.add_head("修复类型", "name", css_class_field="name_class", width="20%")
        table.add_head("修复信息", "content", width="60%")
        table.add_action("修复", link_field="repair_url", type=TableActionType.confirm, 
                         msg_field="repair_msg", css_class="btn danger")
        
        for row in self.repair_rows:
            row.do_content()
            table.add_row(row)

        kw = Storage()
        kw.table = table
        kw.page = 1
        kw.page_max = 1
        kw.page_url = "?page="

        return self.response_page(**kw)
    
    def handle_repair(self):
        code = xutils.get_argument_str("code")
        for item in self.repair_rows:
            if item.code == code:
                return item.do_repair()
        return webutil.FailedResult(code="404", message="没有找到对应的操作")


xurls = (
    "/admin/repair", RepairHandler
)