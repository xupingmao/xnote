/**
 * xnote全局初始化
 * @author xupingmao
 * @since 2022/01/09 16:17:02
 * @modified 2022/04/04 20:35:00
 * @filename x-init.js
 */

/** 初始化全局对象 **/
if (window.xnote === undefined) {
    // 全局对象
    window.xnote = {};
    // 后端接口API模块
    window.xnote.api = {};
    // 表格模块
    window.xnote.table = {};
    // 编辑器模块
    window.xnote.editor = {};
    // 状态
    window.xnote.state = {};

    // 内部属性
    window.xnote._dialogIdStack = [];
}


xnote.registerApiModule = function (name) {
    if (xnote.api[name] === undefined) {
        xnote.api[name] = {};
    }
};


xnote.isEmpty = function (value) {
    return value === undefined || value === null || value === "";
};

xnote.isNotEmpty = function (value) {
    return !xnote.isEmpty(value);
};
