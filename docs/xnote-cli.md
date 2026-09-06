# xnote-cli 设计

## 设计目标

通过 cli 命令来操作 xnote，支持如下功能：

1. 登录与会话：通过 `xnote-cli login` 登录，用户输入用户名和密码后发起 HTTP 请求，
   验证通过后把会话信息（服务端地址、用户名、会话 cookie）保存在
   `${user_home}/.xnote-cli/session.json`。
2. 文档操作：查看、搜索、编辑、删除文档（作为服务端远程命令提供）。
3. 运维指令：备份、数据修复（重建索引）、数据同步（作为服务端远程命令提供）。
4. 插件机制：服务端插件可以在被导入时主动调用 `xnote_cli.register_cmd` 动态注册命令。
5. 命令帮助：`xnote-cli help` / `xnote-cli list` 列出所有可用命令。

## 命令分类：本地命令 vs 远程命令

xnote-cli 的命令分为两类：

### 本地命令（客户端命令）

在 CLI 客户端本地解析并执行，**不依赖服务端命令列表**。目前包括：

| 命令        | 说明                         |
|-------------|------------------------------|
| `login`     | 登录到 xnote 服务端          |
| `logout`    | 退出登录                     |
| `version`   | 查看客户端版本号             |
| `help`/`list` | 查看帮助 / 列出所有命令    |
| `session`   | 查看当前会话信息（直接输出 JSON） |
| `refresh`   | 刷新远程命令列表（重新从服务端拉取并缓存） |

本地命令在 `xnote_cli/commands.py` 的 `register_builtin_commands()` 中通过
`xnote_cli.register_cmd` 注册，只存在于客户端进程。

### 远程命令（服务端命令）

由**服务端**提供，客户端启动时并不知道具体有哪些远程命令，而是：

1. **服务端插件自注册**：插件模块放在 `xnote_handlers/cli/plugins/` 下，在文件中
   `import xnote_cli` 并调用 `xnote_cli.register_cmd(name, handler, help)` 即可注册。
   这些模块由服务端的模块自动发现机制（`xmanager.load_model_dir` 递归导入
   `xnote_handlers` 下的所有 `.py`）在导入时自动注册，无需在核心代码里手动遍历加载。
2. **客户端获取列表**：客户端通过 `/api/cli/command_list` 接口拿到服务端注册的命令
   列表（name + help）。
3. **登录时缓存**：`login` 成功后，客户端会把远程命令列表缓存进会话
   （`session.json` 的 `commands` 字段），之后的命令分发与帮助展示直接复用缓存，
   避免每次请求都拉取。
4. **执行时转发**：执行远程命令时，客户端通过 `/api/cli/run` 接口把命令名与参数
   转发到服务端，由服务端对应的 handler 在登录用户上下文中执行。

当前内置的远程命令（由 `xnote_handlers/cli/plugins/` 下的插件注册）：

| 命令           | 说明             | 插件文件            |
|----------------|------------------|---------------------|
| `note-view`    | 查看笔记内容     | `note_plugin.py`    |
| `note-search`  | 搜索笔记         | `note_plugin.py`    |
| `note-edit`    | 编辑笔记内容     | `note_plugin.py`    |
| `note-delete`  | 删除笔记         | `note_plugin.py`    |
| `note-list`    | 按父文档id列出子文档列表（无参/0 列出根目录） | `note_plugin.py` |
| `backup`       | 备份数据         | `ops_plugin.py`     |
| `repair`       | 修复数据（暂未实现） | `ops_plugin.py` |
| `sync`         | 触发数据同步（暂未实现） | `ops_plugin.py`     |
| `hello`        | 示例插件命令     | `sample_plugin.py`  |

远程命令采用**一级（扁平）子命令**风格，例如 `note-view`、`note-search`，
不使用 `note view` 这种带空格的多级写法。

## 命令分发流程

`xnote-cli` 使用 `argparse` 解析子命令，`-h` 可查看每个子命令的帮助：

```
xnote-cli [-h] <command> [args...]
   │
   ├─ 无子命令 / -h → 打印帮助（本地命令 + 缓存的远程命令）
   │
   ├─ 构建 argparse 解析器：
   │     ├─ 本地命令（COMMANDS 中注册）作为子命令
   │     └─ 已登录时，把会话缓存的远程命令也注册为子命令
   │
   ├─ 子命令命中本地命令表（COMMANDS）
   │     └─ 本地 handler 执行（login/logout/version/help/list）
   │
   └─ 子命令命中远程命令列表
         └─ /api/cli/run 转发到服务端执行（携带登录 cookie；
            远程命令在服务端登录用户上下文中运行）
```

> 说明：`argparse` 会对未知子命令直接报错退出（标准 CLI 行为）。
> 远程命令在登录后才会注册为子命令，因此未登录时直接执行远程命令会提示
> “无效选择”，需先 `xnote-cli login`。

## 约束条件

1. 核心逻辑在 `xnote_cli` 模块下。
2. 处理器逻辑（含服务端远程命令的实现）在 `xnote_handlers` 模块下。
3. 入口在根目录 `xnote-cli.py`：
   ```py
   import sys
   import xnote_cli
   sys.exit(xnote_cli.main())
   ```
4. 服务端远程命令直接调用 `xnote_handlers` 内部的 dao / service 逻辑，
   不通过 HTTP 二次请求自身 REST 接口；鉴权基于 `/api/cli/run` 的登录态。
5. 服务端远程命令 handler 通过 `raise xnote_cli.XnoteCliError(msg)` 表达业务错误，
   由 `RunApiHandler` 转换为失败响应（客户端打印“操作失败：<message>”）。

## 服务端接口

统一放在 `xnote_handlers/cli/cli_api.py`，URL 形如 `/api/cli/xxx`：

| 接口                 | 说明                                         |
|----------------------|----------------------------------------------|
| `/api/cli/login`     | 登录，成功后在 `Set-Cookie` 下发 `sid` 等会话 cookie |
| `/api/cli/logout`    | 退出登录                                     |
| `/api/cli/command_list` | 列出服务端注册的远程命令（name + help）    |
| `/api/cli/run`       | 执行某个远程命令（参数 `cmd` / `args`）      |
| `/api/cli/backup`    | 触发备份                                     |
| `/api/cli/repair`    | 触发索引修复（暂未实现）                     |
| `/api/cli/sync`      | 触发数据同步（暂未实现）                     |

接口统一通过 `webutil.SuccessResult` / `webutil.FailedResult` 返回，
前端/客户端以 `resp.success` 判断是否成功。

客户端把 HTTP 响应解析为结构化的 `ApiResult` 对象
（`xnote_cli.ApiResult`，字段含 `success` / `code` / `message` / `data`），
而不是裸 dict；通过 `ApiResult.from_dict` 与 JSON 互转，`print_result`
等函数直接访问其属性，避免到处 `dict.get(...)`。会话 likewise 用结构化
的 `SessionInfo`（`server_url` / `username` / `cookie` / `commands`）表示，
通过 `to_dict` / `from_dict` 持久化到 `session.json`。

## 会话与 cookie

- 登录成功后，`Set-Cookie` 可能同时包含 `sid` 与 `sid_list` 多个 cookie。
  客户端用 `resp.headers.get_all("Set-Cookie")` 收集所有 cookie，并提取
  `sid`（服务端鉴权实际使用）与 `sid_list`，拼成后续请求的 `Cookie` 头。
- 会话文件 `${user_home}/.xnote-cli/session.json` 结构：
  ```json
  {
    "server_url": "http://localhost:1234",
    "username": "admin",
    "cookie": "sid=xxx; sid_list=xxx",
    "commands": { "note-view": "查看笔记内容", "...": "..." }
  }
  ```
- `logout` 会清空会话文件。

## 示例代码

```py
import xnote_cli
from xnote_cli import XnoteCliContext

def note_view_handler(ctx: XnoteCliContext):
    # 服务端远程命令：直接调用内部逻辑，错误用 XnoteCliError 表达
    note = dao.get_by_id(ctx.args[0])
    if note is None:
        raise xnote_cli.XnoteCliError("笔记不存在")
    # 返回值会作为 ApiResult.data（由 RunApiHandler 统一包装）
    return note.content

# 插件在被导入时主动注册（无需核心代码手动加载）
xnote_cli.register_cmd("note-view", note_view_handler, "查看笔记内容")
```

客户端侧发起请求拿到的是结构化对象，而非裸 dict：

```py
import xnote_cli

resp = xnote_cli.request(ctx, "POST", "/api/cli/run",
                         data={"cmd": "note-view", "args": note_id})
if resp.success:
    print(resp.data)      # 业务数据
else:
    print("执行失败：%s" % resp.message)
```
