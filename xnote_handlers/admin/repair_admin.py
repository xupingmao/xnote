# encoding=utf-8

import xutils
from typing import List
from xutils import webutil
from xutils import Storage
from xnote.core import xtemplate
from xnote.core import xauth
from xnote.service import DatabaseLockService, JobService, JobInfoDO, JobStatusEnum
from xnote.plugin.table_plugin import BaseTablePlugin
from xnote.plugin import DataTable, FormRowType, TableActionType
from xnote_handlers.message.dao import MessageDao, MsgTagInfoDao
from xnote_handlers.message.message_utils import process_message
from xnote_handlers.message import message_tag
from xnote_handlers.config import LinkConfig
from xnote_handlers.note.dao_tag import NoteTagBindDao, NoteTagInfoDao

class BaseRepairTool(Storage):
    def __init__(self, code="", name="", content=""):
        super().__init__()
        self.code = code
        self.name = name
        self.content = content
        self.repair_url = f"?action=repair&code={self.code}"
        self.repair_msg = f"确认修复【{self.name}】吗?"

    def update_content(self):
        """更新修复内容"""
        pass

    def do_repair(self):
        """执行修复动作"""
        return webutil.SuccessResult(message="修复成功")

class RepairMsgTag(BaseRepairTool):
    def update_content(self):
        job_info = JobService.get_latest_job(job_type=self.code)
        if job_info != None:
            self.content = f"修复时间:{job_info.mtime},修复结果:{job_info.job_result}"
        else:
            self.content = "未进行修复"
    
    def do_repair(self):
        with DatabaseLockService.lock(lock_key=self.code, timeout_seconds=60) as lock:
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
                
                for tag_info in MsgTagInfoDao.iter():
                    message_tag.update_tag_amount(tag_info=tag_info, user_id=tag_info.user_id, key = tag_info.tag_code)

                job_info.job_result = f"修复{count}条记录"

        return webutil.SuccessResult(message="修复成功")
    

class RepairNoteTag(BaseRepairTool):
    def update_content(self):
        job_info = JobService.get_latest_job(job_type=self.code)
        if job_info != None:
            self.content = f"修复时间:{job_info.mtime},修复结果:{job_info.job_result}"
        else:
            self.content = "未进行修复"
    
    def do_repair(self):
        with DatabaseLockService.lock(lock_key=self.code, timeout_seconds=60) as lock:
            job_info = JobInfoDO()
            job_info.job_type = self.code
            job_info.job_params = ""
            count = 0
            with JobService.run_with_job(job_info):
                for user_info in xauth.UserDao.iter():
                    tag_dict = dict()
                    for tag_info in NoteTagBindDao.iter(user_id=user_info.user_id):
                        tag_code = tag_info.tag_code.lower()
                        tag_dict[tag_code] = tag_dict.get(tag_code, 0) + 1
                    
                    for tag_code in tag_dict:
                        amount = tag_dict[tag_code]
                        NoteTagInfoDao.update_tag_amount(user_id=user_info.user_id, tag_code=tag_code, amount=amount)
                        count += 1

                job_info.job_result = f"修复{count}条记录"

        return webutil.SuccessResult(message="修复成功")

class RepairHandler(BaseTablePlugin):

    title = "数据修复"
    show_aside = True
    require_admin = True
    parent_link = LinkConfig.app_index

    repair_rows: List[BaseRepairTool] = [
        RepairMsgTag(code="fix_msg_tag", name="待办/随手记索引"),
        RepairNoteTag(code="fix_note_tag", name="笔记标签索引"),
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
            row.update_content()
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