/**
 * 解析URL参数
 * @param {string} src 输入的URL
 * @param {boolean} doDecode 是否进行decode操作
 * @returns {object} 解析之后的对象
 */
xnote.parseUrl = function(src, doDecode) {
    // URL的完整格式如下
    // 协议://用户名:密码@子域名.域名.顶级域名:端口号/目录/文件名.文件后缀?参数=值#标志
    var path = '';
    var args = {};
    // 0: path状态; 1: argName状态; 2: argValue状态;
    var state = 0;
    var name = '';
    var value = '';

    // 默认不进行decode（兼容原来的逻辑）
    if (doDecode === undefined) {
        doDecode = false;
    }

    for(var i = 0; i < src.length; i++) {
        var c = src[i]

        // 状态判断
        if (c == '?' || c == '&') {
            state = 1; // arg name;
            if (name != '') {
                args[name] = value; 
            }
            name = '';
            continue;
        } else if (c == '=') { // arg value
            state = 2; 
            value = '';
            continue;
        }

        // 状态处理
        if (state == 0) {
            path += c; // path state
        } else if (state == 1) {
            name += c; // arg name;
        } else if (state == 2) {
            value += c;
        }
    }

    function formatValue(value) {
        if (doDecode) {
            return decodeURIComponent(value);
        } else {
            return value;
        }
    }

    if (name != '') {
        args[name] = formatValue(value);
    }
    return {'path': path, 'param': args};
}



/**
 * 获取请求参数
 */
xnote.getUrlParams = function() {
    var params = {};
    var url = window.location.href;
    url = url.split("#")[0];
    var idx = url.indexOf("?");
    if(idx > 0) {
        var queryStr = url.substring(idx + 1);
        var args = queryStr.split("&");
        for(var i = 0, a, nv; a = args[i]; i++) {
            nv = args[i] = a.split("=");
            if (nv.length > 1) {
                var value = nv[1];
                try {
                    params[nv[0]] = decodeURIComponent(value);
                } catch (e) {
                    params[nv[0]] = value;
                    console.warn('decode error', e)
                }
            }
        }
    }
    return params;
};

/**
 * 根据key获取url参数值 
 * @param {string} key
 * @param {string} defaultValue 默认值
 */
xnote.getUrlParam = function (key, defaultValue) {
    var paramValue = xnote.getUrlParams()[key];
    if (paramValue === undefined) {
        return defaultValue;
    } else {
        return paramValue;
    }
}

/**
 * 给指定的url添加参数
 * @param {string} url 指定的url
 * @param {string} key 参数的key
 * @param {string} value 参数的value
 */
xnote.addUrlParam = function(url, key, value) {
    var parsed = parseUrl(url);
    var result = parsed.path;
    var params = parsed.param;
    var isFirst = true;
    
    params[key] = encodeURIComponent(value);
    // 组装新的url
    for (var key in params) {
        var paramValue = params[key];
        if (isFirst) {
            result += "?" + key + "=" + paramValue;
            isFirst = false;
        } else {
            result += "&" + key + "=" + paramValue;
        }
    }
    return result;
}

/**
 * HTML转义
 * @param {string} text 待转义的文本
 * @returns {string}
 */
xnote.escapeHTML = function (text) {
    return $("<div>").text(text).html();
}

window.parseUrl = xnote.parseUrl
window.getUrlParam = xnote.getUrlParam
window.getUrlParams = xnote.getUrlParams
window.addUrlParam = xnote.addUrlParam
