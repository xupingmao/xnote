# xnote_handlers/message 模块功能总结

## 目录结构

| 文件 | 说明 |
|------|------|
| `__init__.py` | 空包标记 |
| `service.py` | 空占位文件 |
| `message.py` | 主入口：34 个 URL 路由，页面处理器 + AJAX 端点 |
| `message_model.py` | 数据模型与枚举（MessageDO、MsgIndex、MsgTagInfo 等） |
| `message_utils.py` | 工具函数：文本解析、HTML 渲染、标签处理 |
| `dao.py` | 数据访问层：KV + SQL 双存储，CRUD、搜索、统计 |
| `dao_filter.py` | 标签过滤器配置 DAO |
| `dao_template.py` | 消息模板 DAO |
| `message_tag.py` | 标签管理：增删、列表、搜索、过滤器编辑 |
| `message_search.py` | 搜索逻辑 + 全局搜索钩子 |
| `message_task.py` | 任务视图：创建、完成、标签列表 |
| `message_date.py` | 日期视图：日历、按日分组、日期详情 |
| `message_log.py` | 随手记（日志）页面处理器 |
| `message_tab.py` | Tab 导航栏构建器 |
| `message_template.py` | 消息模板 CRUD（基于 BaseTablePlugin） |
| `message_template_service.py` | 模板 Tab 注入到页面上下文 |

## 整体架构

"消息"系统（随手记）是一个**统一的笔记、任务管理和日志子系统**，支持四种主要内容类型：

| 标签 | 显示名称 | 用途 |
|------|---------|------|
| `task` | 待办任务 | 支持完成/重开生命周期 |
| `done` | 已完成 | 已完成的任务（引用回原始任务） |
| `log` | 随手记 | 自由格式的日记/日志条目 |
| `key` | 话题 | 标签元数据实体 |

## 数据存储架构（双存储）

1. **SQL 索引表** (`msg_index` via `MsgIndexDao`)：按用户、标签、日期范围快速过滤和排序
2. **KV 内容表** (`msg_v3`)：完整的消息内容及所有字段
3. **标签信息**：存储在 `tag_info` 表 (`MsgTagInfoDao`)，绑定关系在 `MsgTagBindService`
4. **历史版本**：存储在 `msg_history` KV 表
5. **统计缓存**：存储在 `user_stat` KV 表

## 核心功能

1. **完整 CRUD** — 创建、读取、更新、删除消息，支持版本历史
2. **任务管理** — 标记完成/重开，带有生命周期注释（`$mark_task_done$`、`$reopen_task$`）
3. **标签系统** — `#tag#` 语法，自动检测 `@人名`、URL、`《书名》`、手机号、文件路径
4. **日期组织** — 消息可回溯日期；日历和日记视图按日/月分组
5. **搜索** — 全文搜索，关键词高亮，搜索历史记录，全局搜索集成
6. **标签过滤** — 三级标签过滤器（tag1/tag2/tag3），持久化为用户配置
7. **模板** — 用户定义的消息模板，支持快速录入（log 和 task 类型）
8. **评论** — 每条消息下的评论线程，支持增删
9. **统计** — 按用户的计数统计，缓存在导航 Tab 中显示
10. **关键字/标记** — 收藏标签可标记（基于评分），按访问量、最近使用或使用次数排序
11. **系统标签** — 自动检测类别：`_book`、`_people`、`_file`、`_phone`、`_link`
12. **移动端支持** — 响应式布局，条件渲染

## 各模块详细说明

### message.py — 主编排器

34 个 URL 路由，核心处理器：

| 路由 | 处理器 | 方法 | 说明 |
|------|--------|------|------|
| `/message` | `MessagePageHandler` | GET | 主路由，按 tag 参数分发到各视图 |
| `/message/list` | `ListAjaxHandler` | GET | 主要 AJAX 数据端点，支持搜索/过滤/分页 |
| `/message/save` | `SaveAjaxHandler` | POST | 创建或更新消息 |
| `/message/delete` | `DeleteAjaxHandler` | POST | 删除消息（保留历史） |
| `/message/finish` | `FinishMessageAjaxHandler` | POST | 标记任务完成 |
| `/message/open` | `OpenMessageAjaxHandler` | POST | 重开任务 |
| `/message/touch` | `TouchAjaxHandler` | POST | 更新修改时间 |
| `/message/comment/*` | 三个处理器 | POST | 评论 CRUD |

### message_model.py — 数据模型

- **`MessageTagEnum`** — 一级标签枚举：`task`、`done`、`log`；系统标签：`_book`、`_people`、`_file`、`_phone`、`_link`
- **`MessageDO`** — 主要消息实体，含 `tag`、`content`、`comments`、`keywords`、`files` 等字段
- **`MsgIndex`** — SQL 索引记录
- **`MsgTagInfo`** — 用户定义标签信息，含 `score`（标记评分）、`amount`（使用次数）
- **`TagFilterConfig`** — 三级过滤配置

### message_utils.py — 工具函数

- **`TagHelper`** — 显示标签与搜索标签之间的映射
- **`mark_text()` / `mark_text_v2()`** — 核心文本转 HTML 转换，识别标签、链接、电话等
- **`MessageListParser`** — 消息列表预处理：迁移旧状态、自动检测系统标签
- **`get_tags_from_message_list()`** — 从消息列表收集标签并统计使用次数
- **`convert_message_list_to_day_folder()`** — 将消息按天分组

### dao.py — 数据访问层

- **`MessageDao`** — 消息 CRUD 静态方法
- **`MsgIndexDao`** — SQL 索引表操作
- **`MsgTagInfoDao`** — 标签信息 CRUD
- **`MsgTagBindDao`** — 标签与消息的绑定关系
- **`MsgSearchLogDao`** — 搜索历史记录

### message_tag.py — 标签管理

8 个路由，功能包括：添加标签、删除标签、标签列表（按类别分组）、系统标签查看、标签搜索、过滤器编辑。

### message_search.py — 搜索

- 全局搜索钩子 `on_search_message()`，同时搜索任务和日志
- `SearchHandler` 处理搜索页面和 AJAX 数据

### message_task.py — 任务视图

4 个路由：任务主页面、已完成任务、任务列表 AJAX、任务标签索引。支持 `filterKey` 多标签过滤。

### message_date.py — 日期视图

4 个路由：按日分组、日历月视图、日期详情。

### message_log.py — 随手记页面

主要日志页面，集成侧边标签、过滤 Tab、模板 Tab。

### message_template.py — 模板管理

基于 BaseTablePlugin 的模板 CRUD，支持类型（全部/随手记/待办）、排序、编辑。
