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
        leftNavWidth: 0, // 左侧导航宽度
        end: 0
    };

    // 配置信息
    xnote.config = {};
    xnote.config.serverHome = "";
    
    // 内部属性
    xnote._dialogIdStack = [];

    // 常量
    xnote.MOBILE_MAX_WIDTH = 1000;
    xnote.constants = {
        MOBILE_MAX_WIDTH: 100
    };

    // 后端接口API模块
    xnote.api = {};
    // 操作动作接口
    xnote.action = {};

    // 事件相关接口
    xnote.events = {};
    // resize事件回调
    xnote.events.resizeHooks = [];

    // 表格模块
    xnote.table = {};
    // 编辑器模块
    xnote.editor = {};
    // 业务状态
    xnote.state = {};
    // 系统状态
    xnote.state.system = {};
    // 按键弹起的时间
    xnote.state.system.keyupTime = new Date().getTime();

    // http相关操作
    xnote.http = {};

    // 功能模块
    xnote.note = {};

    // 字符串模块
    xnote.string = {};
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



// 调整表格宽度
xnote.table.adjustWidth = function(selector) {
    $(selector).each(function (element, index) {
        var headings = $(this).find("th");
        if (headings.length > 0) {
            var width = 100 / headings.length;
            headings.css("width", width + "%");
        }
    });
};

/**
 * 追加CSS样式表
 * @param {string} styleText 样式文本
 */
xnote.appendCSS = function (styleText) {
    // 居中的样式
    var style = document.createElement("style");
    style.type = "text/css";

    if (style.styleSheet) {
      // 兼容IE
      style.styleSheet.cssText = styleText;  
    } else {  
      style.innerHTML = styleText;
    } 

    document.head.appendChild(style);
};

xnote.http.defaultFailHandler = function (err) {
    console.log(err);
    xnote.toast("服务器繁忙, 请稍后重试~");
};

// http-post请求
xnote.http.post = function (url, data, callback, type) {
    return $.post(xnote.config.serverHome + url, data, callback, type).fail(xnote.http.defaultFailHandler);
}

// http-get请求
xnote.http.get = function (url, data, callback, type) {
    return $.get(xnote.config.serverHome + url, data, callback, type).fail(xnote.http.defaultFailHandler);
}

xnote.isTyping = function() {
    var now = new Date().getTime();
    var typingGap = 200; // 200毫秒
    return now - xnote.state.system.keyupTime < typingGap;
}

var XUI = function(window) {
    // 处理select标签选中情况
    function initSelect() {
        $("select").each(function(index, ele) {
            var self = $(ele);
            var children = self.children();
            // 使用$.val() 会取到第一个select标签值
            var value = self.attr("value");
            for (var i = 0; i < children.length; i++) {
                var child = children[i];
                if (value == child.value) {
                    child.selected = "selected";
                }
            }
        });
    }

    function initCheckbox() {
        $("input[type=checkbox]").each(function(index, ele) {
            var self = $(ele);
            var value = self.attr("default-value");
            if (value == "on") {
                self.attr("checked", "checked");
            }
        })
    }

    function initRadio() {
        $("input[type=radio]").each(function(index, ele) {
            var self = $(ele);
            var value = self.attr("default-value");
            if (value == self.val()) {
                self.attr("checked", "checked");
            }
        });
    }

    function initXRadio() {
        $(".x-radio").each(function(index, element) {
            var self = $(element);
            var option = self.attr("data-option");
            var value = self.attr("data-value");
            if (value == option) {
                self.addClass("selected-link");
            }
        });
    };

    // 点击跳转链接的按钮
    $(".link-btn").click(function() {
        var link = $(this).attr("x-href");
        if (!link) {
            link = $(this).attr("href");
        }
        var confirmMessage = $(this).attr("confirm-message");
        if (confirmMessage) {
            xnote.confirm(confirmMessage, function (result) {
                window.location.href = link;
            });
        } else {
            window.location.href = link;
        }
    });

    // 点击prompt按钮
    // <input type="button" class="prompt-btn" action="/rename?name=" message="重命名为" value="重命名">
    $(".prompt-btn").click(function() {
        var action = $(this).attr("action");
        var message = $(this).attr("message");
        var defaultValue = $(this).attr("default-value");
        var inputValue = prompt(message, defaultValue);
        if (inputValue != "" && inputValue) {
            var actionUrl = action + encodeURIComponent(inputValue);
            $.get(actionUrl, function(resp) {
                window.location.reload();
            })
        }
    });

    // 初始化表单控件的默认值
    function initDefaultValue(event) {
        initSelect();
        initCheckbox();
        initRadio();
        initXRadio();
        xnote.table.adjustWidth(".default-table");
    };

    window.xnote.assert = function (expression, message) {
        if (!expression) {
            xnote.alert(message);
        }
    };

    // 刷新各种默认值
    xnote.refresh = function () {
        // 初始化
        initDefaultValue();
        // 注册事件
        xnote.addEventListener("init-default-value", initDefaultValue);
        xnote.addEventListener("xnote.reload", initDefaultValue);
    };

    xnote.refresh();
};

$(document).ready(function() {
    XUI(window);
    $("body").on("keyup", function (event) {
        xnote.state.system.keyupTime = new Date().getTime();
    });
});

/**
 * 指定索引对文本进行替换
 * @param {string} text 原始文本
 * @param {string} target 被替换的文本
 * @param {string} replacement 新的文本
 * @param {int} index 索引位置
 * @returns 
 */
xnote.string.replaceByIndex = function (text, target, replacement, index) {
    var tokens = text.split(target);
    var result = [];
    for (var i = 0; i < tokens.length; i++) {
        var token = tokens[i];
        result.push(token);

        if (i+1 == tokens.length) {
            continue;
        }

        if (i == index) {
            result.push(replacement);
        } else {
            result.push(target);
        }
    }
    
    return result.join("");
};

