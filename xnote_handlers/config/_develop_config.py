# -*- coding: utf-8 -*-
"""开发者工具宫格配置（挂在 xnote_handlers.config 下统一管理）"""
from xnote.plugin.grid import AppInfo


# 开发者工具分类（宫格项）
DEVELOPER_APPS = [
    AppInfo(name="浏览器信息", url="/tools/browser_info",                 icon="globe"),
    AppInfo(name="图片工具",   url="/tools/img_merge?tab=merge&nav=true", icon="image"),
    AppInfo(name="编解码工具", url="/tools/encode?tab=BASE64&nav=true",    icon="exchange"),
    AppInfo(name="文本工具",   url="/tools/text_convert?tab=convert&nav=true", icon="file-text-o"),
    AppInfo(name="前端组件",   url="/examples",                    icon="cubes"),
    AppInfo(name="系统模块",   url="/system/module_list",                 icon="sitemap"),
    AppInfo(name="性能分析",   url="/system/handler_profile",             icon="tachometer"),
    AppInfo(name="内存分析",   url="/system/trace_malloc",                 icon="microchip"),
]
