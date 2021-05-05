
function parseUrl(src) {
    // URL的完整格式如下
    // 协议://用户名:密码@子域名.域名.顶级域名:端口号/目录/文件名.文件后缀?参数=值#标志
    var path = '';
    var args = {};
    // 0: path状态; 1: argName状态; 2: argValue状态;
    var state = 0;
    var name = '';
    var value = '';
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
    if (name != '') {
        args[name] = value;
    }
    return {'path': path, 'param': args};
}



/**
 * 获取请求参数
 */
var getUrlParams = function() {
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
 */
var getUrlParam = function (key) {
    return getUrlParams()[key];
}
