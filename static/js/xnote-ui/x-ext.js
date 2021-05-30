/**
 * xnote扩展函数
 * @author xupingmao
 * @since 2021/05/30 14:39:39
 * @modified 2021/05/30 14:42:19
 * @filename x-ext.js
 */

if (window.xnote == undefined) {
    window.xnote = {};
}

xnote.EXT_DICT = {};

window.xnote.getExtFunc = function (funcName) {
    return xnote.EXT_DICT[funcName];
}

window.xnote.setExtFunc = function (funcName, func) {
    xnote.EXT_DICT[funcName] = func;
}