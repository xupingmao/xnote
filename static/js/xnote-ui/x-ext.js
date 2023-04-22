/**
 * xnote扩展函数
 * @author xupingmao
 * @since 2021/05/30 14:39:39
 * @modified 2022/01/09 16:08:42
 * @filename x-ext.js
 */

xnote.EXT_DICT = {};

xnote.getExtFunc = function (funcName) {
    return xnote.EXT_DICT[funcName];
};

xnote.setExtFunc = function (funcName, func) {
    xnote.EXT_DICT[funcName] = func;
};
