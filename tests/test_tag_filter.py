# -*- coding:utf-8 -*-
# encoding=utf-8

import pytest
from tests.test_base import BaseTestCase, json_request_return_dict
from xutils import jsonutil

class TestTagFilter(BaseTestCase):
    """测试标签过滤器功能"""
    
    def test_tag_filter_edit_page(self):
        """测试标签过滤器编辑页面"""
        # 先登录
        self.request_app("/")
        
        # 访问标签过滤器编辑页面 - task.filter
        response = self.request_app("/message/tag/filter?action=edit&filter_config_key=task.filter")
        self.assertEqual("200 OK", response.status)
        
        # 检查返回的HTML中是否包含表单字段
        html = response.data.decode("utf-8")
        self.assertIn('name="tag1"', html)
        self.assertIn('name="tag2"', html)
        self.assertIn('name="tag3"', html)
        self.assertIn('filter_config_key', html)
        self.assertIn('value="task.filter"', html)
    
    def test_tag_filter_msg_edit_page(self):
        """测试随手记过滤器编辑页面"""
        # 先登录
        self.request_app("/")
        
        # 访问随手记过滤器编辑页面 - msg.filter
        response = self.request_app("/message/tag/filter?action=edit&filter_config_key=msg.filter")
        self.assertEqual("200 OK", response.status)
        
        # 检查返回的HTML中是否包含表单字段
        html = response.data.decode("utf-8")
        self.assertIn('name="tag1"', html)
        self.assertIn('name="tag2"', html)
        self.assertIn('name="tag3"', html)
        self.assertIn('value="msg.filter"', html)
    
    def test_tag_filter_save_json_format(self):
        """测试标签过滤器保存功能 - JSON 格式"""
        # 先登录
        self.request_app("/")
        
        param_dict = {
            "filter_config_key": "task.filter",
            "tag1": "标签1,标签2\n标签3",
            "tag2": "随手记标签1 随手记标签2",
            "tag3": ""
        }
        
        # 保存标签过滤器 - 使用新的 JSON 格式
        response = json_request_return_dict(
            "/message/tag/filter?action=save&model=filter",
            method = "POST",
            data = dict(data = jsonutil.tojson(param_dict)),
        )
        
        # 检查返回的结果是否是成功
        self.assertEqual("success", response.get("code"))
        
        # 再次访问编辑页面，验证数据已保存
        response = self.request_app("/message/tag/filter?action=edit&filter_config_key=task.filter")
        html = response.data.decode("utf-8")
        self.assertIn('标签1', html)
        self.assertIn('标签2', html)
        self.assertIn('标签3', html)
    
    def test_tag_filter_compatibility(self):
        """测试标签过滤器兼容旧的纯文本格式"""
        # 先登录
        self.request_app("/")
        
        param_dict = {
            "filter_config_key": "task.filter",
            "tag1": "旧标签1 旧标签2",
            "tag2": "",
            "tag3": ""
        }
        
        # 手动设置一个旧的纯文本格式的 task.filter
        response = json_request_return_dict(
            "/message/tag/filter?action=save&model=filter",
            method="POST",
            data=dict(data = jsonutil.tojson(param_dict))
        )
        self.assertEqual("success", response.get("code"))
        
        # 访问编辑页面，验证旧格式被正确解析
        response = self.request_app("/message/tag/filter?action=edit&filter_config_key=task.filter")
        html = response.data.decode("utf-8")
        self.assertIn('旧标签1', html)
        self.assertIn('旧标签2', html)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
