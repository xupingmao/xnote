/**
 * xnote全局初始化
 * @author xupingmao
 * @since 2022/01/09 16:17:02
 * @modified 2022/02/07 12:21:11
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
}


window.xnote.registerApiModule = function (name) {
    if (xnote.api[name] === undefined) {
        xnote.api[name] = {};
    }
};


