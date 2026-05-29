# xnote-ui 前端库参考

## 文件清单

| 文件 | 层级 | 职责 |
|------|------|------|
| `x-init.js` | 核心 | 命名空间定义、HTTP 封装、全局初始化、工具函数 |
| `x-event.js` | 核心 | 事件派发机制（EventDispatcher） |
| `x-url.js` | 工具 | URL 解析、参数读写、HTML 转义 |
| `x-template.js` | 工具 | 简单模板渲染 + art-template 桥接 |
| `x-device.js` | 工具 | 设备/浏览器检测、窗口尺寸 |
| `x-dialog.js` | UI 组件 | 基于 layer.js 的对话框系统 |
| `x-tab.js` | UI 组件 | Tab 切换（tab-link、tab-btn、tab-box） |
| `x-dropdown.js` | UI 组件 | 下拉菜单（桌面/移动端） |
| `x-table.js` | UI 组件 | 表格行操作：确认、编辑、查看详情 |
| `x-photo.js` | UI 组件 | 点击 `.x-photo` 图片打开相册浏览 |
| `x-layout.js` | UI 组件 | textarea 自动高度、滚动定位 |
| `x-upload.js` | UI 组件 | 文件上传（WebUploader）、剪贴板上传 |
| `x-audio.js` | UI 组件 | 音频播放（layer iframe） |
| `x-ext.js` | 扩展 | 扩展点注册表 |
| `layer.photos.js` | 第三方修改 | layer 相册层（增加旋转、Hammer.js 手势） |
| `x-core.js` | — | **已废弃**，代码已迁移到 `x-init.js` |
| `docs.js` | — | 仅 JSDoc 类型导入声明 |

## 全局命名空间

采用三级结构：`xnote.{module}.{method/field}`

```js
xnote.config       // 运行时配置（serverHome, isPrintMode, nodeRole...）
xnote.state        // 运行时状态（currentId, system.keyupTime...）
xnote.device       // 设备/UA 检测结果
xnote.http         // HTTP 请求封装
xnote.dialog       // 对话框
xnote.table        // 表格
xnote.layout       // 布局
xnote.events       // 事件回调注册表
xnote.editor       // 编辑器
xnote.string       // 字符串工具
xnote.array        // 数组工具
xnote.tmp          // 临时存储空间

// 业务模块（各页面按需扩展）
xnote.note, xnote.comment, xnote.message,
xnote.admin, xnote.view, xnote.file
```

## 初始化流程

1. `x-init.js` 定义 `xnote` 全局对象
2. `$(document).ready( XUI(window) )` 执行表单控件初始化
3. `XUI` 内调用 `xnote.refresh()`，注册 `init-default-value` 和 `xnote.reload` 事件
4. 事件触发时：初始化 select/checkbox/radio 的 value 绑定、调整 `.default-table` 列宽、调用 `xnote.initSelect2` / `xnote.initLaydate`（若定义）

### 关键方法

- `xnote.refresh()` — 手动触发所有控件的默认值刷新
- `xnote.createNewId()` — 自增 ID 生成器
- `xnote.isEmpty(val)` / `xnote.isNotEmpty(val)` — 空值检查
- `xnote.getOrDefault(val, default)` — undefined 时返回默认值
- `xnote.appendCSS(text)` — 动态追加 `<style>`
- `xnote.parseBoolean(text)` — 文本转布尔值

## HTTP 请求

`xnote.http.*` 自动拼接 `xnote.config.serverHome` 前缀。

```js
xnote.http.get(url, data, callback, dataType)
xnote.http.post(url, data, callback, dataType)
xnote.http.ajax(method, url, data, callback, dataType)
xnote.http.internalGet(url, data, callback)    // 无 fail 处理
xnote.http.internalPost(url, data, callback)   // 无 fail 处理
xnote.http.resolveURL(url)                     // 拼接 serverHome
xnote.http.defaultFailHandler(err)             // 默认失败回调：toast 提示
```

## 对话框 API（x-dialog.js）

基于 layer.js 封装，统一管理对话框尺寸适配（桌面 600×80%，移动端 100%×100%）。

### 通用对话框

```js
xnote.showDialog(title, html, buttons, functions)
xnote.showDialogEx(options)
// options:
//   title, html, buttons, functions
//   area — 支持 'large'、'fullscreen'、['宽', '高']、undefined（默认）
//   template — 用 `<template>` 选择器取代 html
//   defaultValues — template 变量填充
//   dialogId, closeBtn, shadeClose, anim, onOpenFn, closeForYes
xnote.showIframeDialog(title, url, buttons, functions)
xnote.showAjaxDialog(title, url, buttons, functions)
xnote.showOptionDialog(option)                 // 选项弹窗，无标题/关闭按钮
```

### 系统对话框替代

```js
xnote.alert(message)
xnote.confirm(message, callback(isYes))
xnote.prompt(title, defaultValue, callback)
xnote.promptTextarea(title, defaultValue, callback)
xnote.toast(message, timeout?, callback?)
```

### 文本对话框

```js
xnote.showTextDialog(title, text, buttons, functions)
xnote.openTextArea(title, defaultValue, callback)  // = promptTextarea
```

### 关闭弹窗

```js
xnote.closeDialog(layerIndex)
xnote.closeDialog("last")
xnote.closeAllDialog()
```

### HTML 属性驱动

`<button class="dialog-btn" dialog-url="..." dialog-title="...">` 自动加载 URL 内容并弹窗。

## Tab 组件（x-tab.js）

支持三种样式类，HTML 结构约定：

| CSS 类 | 行为 |
|--------|------|
| `.x-tab-btn` | 匹配当前 URL path+search 自动激活，无匹配时 `.x-tab-default` 激活 |
| `.x-tab-box` | 通过 `data-tab-key` 读取 URL 参数自动激活，参数不存在用 `data-tab-default`；带 `data-content-id` 的子项切换内容区 |
| `.x-tab-link` | 声明式，框架自动加 `href` 参数 |

## 下拉菜单（x-dropdown.js）

```html
<div class="dropdown" onclick="xnote.toggleDropdown(this)">
  <button class="dropdown-btn">菜单</button>
  <div class="dropdown-content">...</div>
</div>
```

- 桌面端：`slideDown` / `slideUp`
- 移动端（`.mobile` 类）：动画从底部升起 60% 高度，锁定 body 滚动
- 点击 `.dropdown-content` 以外的区域自动关闭

## 表格操作（x-table.js）

HTML 属性驱动，用于表格行内的操作按钮：

```html
<button data-method="POST" data-url="/api/action"
        data-msg="确认操作？" data-reload-url="/page"
        onclick="xnote.table.handleConfirmAction(this, event)">
  操作
</button>
```

| 方法 | 作用 |
|------|------|
| `xnote.table.handleConfirmAction(target, event)` | 弹出确认框 → POST/GET 请求 → toast/alert 提示 → 跳转/刷新 |
| `xnote.table.handleAction(target)` | 打开 iframe 对话框 |
| `xnote.table.handleEditForm(target)` | 加载 URL 内容到对话框编辑 |
| `xnote.table.handleViewDetail(target)` | 查看详情文本对话框 |

## 图片浏览（x-photo.js + layer.photos.js）

`x-photo.js` 点击 `.x-photo` 图片打开相册。`layer.photos.js` 是修改版，新增功能：

- 图片旋转（点击 "旋转" 按钮，支持 90°/180°/270°/360°）
- 旋转时重绘弹窗尺寸（`repaint` 方法）
- Hammer.js 手势支持（swipeleft/swiperight 翻页）
- 移动端全屏适配
- 上下信息栏（顶部：旋转/关闭按钮；底部：图片名 + 页码）

## 文件上传（x-upload.js）

基于 WebUploader 库封装。

```js
xnote.createUploader(fileSelector, chunked, successFn)
xnote.createUploaderEx({ fileSelector, chunked, successFn, fixOrientation, fileName })
xnote.requestUpload(fileSelector, chunked, successFn, errorFn)
xnote.requestUploadAuto(fileSelector, chunked, successFn, errorFn)  // fileName = "auto"
xnote.requestUploadByOption({ ... })
xnote.requestUploadByClip(event, filePrefix, successFn, errorFn)   // 剪贴板粘贴图片
xnote.uploadBlob(blob, prefix, successFn, errorFn)                 // Blob 直传
```

## URL 工具（x-url.js）

```js
xnote.parseUrl(src, doDecode?)     // => { path, param }
xnote.getUrlParams()               // => 当前 URL 参数对象
xnote.getUrlParam(key, default?)   // 取单个参数
xnote.addUrlParam(url, key, value) // 追加参数
xnote.escapeHTML(text)             // HTML 转义
```

也挂在全局：`parseUrl`, `getUrlParam`, `getUrlParams`, `addUrlParam`

## 模板渲染（x-template.js）

```js
xnote.renderTemplate("Hello,${name}!", {name: "World"})  // => "Hello,World!"
xnote.renderArtTemplate(text, data, options)              // art-template 渲染
```

jQuery 扩展：`$(selector).render(data)` 或 `$(selector).renderTemplate(data)`

## 设备检测（x-device.js）

```js
xnote.getWindowWidth() / getWindowWidth()
xnote.getWindowHeight() / getWindowHeight()
xnote.isDesktop()              // width >= 800
xnote.isMobile()               // width < MOBILE_MAX_WIDTH(1000)
isPc(), isMobile()             // 全局别名
```

浏览器检测（赋值到 `xnote.device`，来自 quark.js）：
`isWebKit`, `isMozilla`, `isIE`, `isFirefox`, `isChrome`, `isSafari`, `isMobile`,
`isOpera`, `isIOS`, `isIpad`, `isIpod`, `isIphone`, `isAndroid`,
`supportStorage`, `supportOrientation`, `supportDeviceMotion`, `supportTouch`, `supportCanvas`

## 布局工具（x-layout.js）

```js
$(textarea).autoHeight()         // 输入时自动调整高度
$(elem).showInScroll(offsetY?)   // 滚动父容器使元素可见

xnote.layout.getTextareaTextHeight(textarea)  // 计算 textarea 内文本高度（克隆法）
```

## 扩展点（x-ext.js）

```js
xnote.setExtFunc("myFunc", fn)
xnote.getExtFunc("myFunc")       // 获取注册的函数
```

## 事件系统（x-event.js）

EventDispatcher 模式（来自 quark.js），`xnote` 内置单例。

```js
xnote.addEventListener(type, listener)
xnote.removeEventListener(type, listener)
xnote.fire(type, target)            // 触发事件
```

内部事件名举例：`init-default-value`、`xnote.reload`

## 音频（x-audio.js）

```html
<div class="x-audio" data-src="...">播放</div>
```

点击 `x-audio` 元素以 layer iframe 打开音频。

```js
xnote.loadAudio(id, src)    // 预加载音频
xnote.playAudio(id)         // 播放
```
