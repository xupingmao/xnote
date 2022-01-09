/**
 * description here
 * @author xupingmao
 * @since 2022/01/09 16:17:02
 * @modified 2022/01/09 16:30:37
 * @filename x-init.js
 */

/** 初始化全局对象 **/
if (window.xnote === undefined) {
    // 全局对象
    window.xnote = {};
    // 初始化API对象
    window.xnote.api = {};
}


window.xnote.registerApiModule = function (name) {
    if (xnote.api[name] === undefined) {
        xnote.api[name] = {};
    }
};


