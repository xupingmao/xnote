/**
 * xnote全局初始化
 * @author xupingmao
 * @since 2022/01/09 16:17:02
 * @modified 2022/04/09 18:15:07
 * @filename x-init.js
 */

/** 初始化xnote全局对象 **/
if (window.xnote === undefined) {
    // 全局对象
    var xnote = {};
    // 后端接口API模块
    xnote.api = {};
    // 表格模块
    xnote.table = {};
    // 编辑器模块
    xnote.editor = {};
    // 状态
    xnote.state = {};

    // 内部属性
    xnote._dialogIdStack = [];

    // 常量
    xnote.MOBILE_MAX_WIDTH = 1000;
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
