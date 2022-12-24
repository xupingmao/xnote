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

    // 设备信息
    xnote.device = {
        contentWidth: 0,     // 内容的宽度，包括左侧主数据和侧边栏
        contentLeftWidth: 0, // 左侧的宽度
        isMobile: false, // 是否是移动端
        isDesktop: true, // 默认是桌面端
        end: 0
    };

    // 内部属性
    xnote._dialogIdStack = [];

    // 常量
    xnote.MOBILE_MAX_WIDTH = 1000;
    xnote.constants = {
        MOBILE_MAX_WIDTH: 100
    };

    // 后端接口API模块
    xnote.api = {};
    // 表格模块
    xnote.table = {};
    // 编辑器模块
    xnote.editor = {};
    // 业务状态
    xnote.state = {};
}

xnote.registerApiModule = function (name) {
    if (xnote.api[name] === undefined) {
        xnote.api[name] = {};
    }
};

/**
 * 注册API
 * @param {string} apiName API名称
 * @param {function} fn 函数
 */
xnote.registerApi = function (apiName, fn) {
    if (xnote.api[apiName] === undefined) {
        xnote.api[apiName] = fn;
    } else {
        var errMessage = "api is registered: " + apiName;
        console.error(errMessage);
        xnote.alert(errMessage);
    }
}

xnote.isEmpty = function (value) {
    return value === undefined || value === null || value === "";
};

xnote.isNotEmpty = function (value) {
    return !xnote.isEmpty(value);
};

xnote.getOrDefault = function (value, defaultValue) {
    if (value === undefined) {
        return defaultValue;
    }
    return value;
};

xnote.execute = function (fn) {
    fn();
};


xnote.validate = {
    "notUndefined": function (obj, errMsg) {
        if (obj === undefined) {
            xnote.alert(errMsg);
            throw new Error(errMsg);
        }
    },
    "isFunction": function (obj, errMsg) {
        if (typeof obj !== 'function') {
            xnote.alert(errMsg);
            throw new Error(errMsg);
        }
    }
};
