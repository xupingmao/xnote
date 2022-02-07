/** 
 * 对话框实现
 * 参考 https://www.layui.com/doc/modules/layer.html
 * 
 * 对外接口:
 * 1. 展示对话框并且自适应设备
 *    xnote.showDialog(title, html, buttons = [], functions = [])
 *    xnote.showDialogEx(options)
 * 
 * 2. 展示iframe页面
 *    xnote.showIframeDialog(title, url)
 *    xnote.showAjaxDialog(title, url, buttons, functions)
 * 
 * 3. 展示选项的对话框
 *    // option参数的定义 {html, title = false}
 *    xnote.showOptionDialog(option)
 * 
 * 4. 系统自带的弹窗替换
 *    xnote.alert(message)
 *    xnote.confirm(message, callback)
 *    xnote.prompt(title, defaultValue, callback)
 *    // 打开文本编辑的对话框
 *    xnote.showTextDialog(title, text, buttons, functions)
 * 
 */


if (window.xnote === undefined) {
    throw new Error("xnote is undefined!");
}

function getDialogArea() {
    if (isMobile()) {
        return ['100%', '100%'];
    } else {
        return ['600px', '80%'];
    }
}

window.xnote.showIframeDialog = function (title, url) {
    var area = getDialogArea();
    return layer.open({
        type: 2,
        shadeClose: true,
        title: title,
        maxmin: true,
        area: area,
        content: url,
        scrollbar: false
    });
}

// 关闭对话框的入口方法
window.xnote.closeDialog = function (flag) {
    if (flag === "last") {
        var lastId = xnote._dialogIdStack.pop();
        layer.close(lastId);
    }

    if (flag instanceof Number) {
        layer.close(flag);
        // TODO 移除_dialogIdStack中的元素
    }
}

window.xnote.showDialogEx = function (options) {
    var dialogId = xnote.showDialogExInner(options);
    xnote._dialogIdStack.push(dialogId);
    return dialogId;
}

window.xnote.showDialogExInner = function (options) {
    var area = getDialogArea();
    var title = options.title;
    var html  = options.html;
    var buttons = options.buttons;
    var functions = options.functions;
    var anim = options.anim;
    var closeBtn = options.closeBtn;

    // 详细文档 https://www.layui.com/doc/modules/layer.html
    // @param {int} anim 动画的参数
    // undefined: 默认动画
    // 0：平滑放大。默认
    // 1：从上掉落
    // 2：从最底部往上滑入
    // 3：从左滑入
    // 4：从左翻滚
    // 5：渐显
    // 6：抖动出现

    if (!(functions instanceof Array)) {
        functions = [functions];
    }

    if (buttons == undefined) {    
        return layer.open({
            type: 1,
            title: title,
            shadeClose: true,
            closeBtn: closeBtn,
            area: area,
            content: html,
            anim: anim,
            // scrollbar是弹层本身的滚动条，不是整个页面的
            scrollbar: false
        });
    } else {
        return layer.open({
            type: 1,
            title: title,
            shadeClose: true,
            closeBtn: closeBtn,
            area: area,
            content: html,
            scrollbar: false,
            btn: buttons,
            anim: anim,
            yes: function (index, layero) {
                console.log(index, layero);
                layer.close(index);
                functions[0](index, layero);
            }
        });
    }
}

xnote.showDialog = function(title, html, buttons, functions) {
    var options = {};
    options.title = title;
    options.html  = html;
    options.buttons = buttons;
    options.functions = functions;
    return xnote.showDialogEx(options);
}

xnote.showTextDialog = function(title, text, buttons, functions) {
    var options = {};
    options.title = title;
    options.html  = "<textarea class=\"dialog-textarea\">" + text + "</textarea>";
    options.buttons = buttons;
    options.functions = functions;
    return xnote.showDialogEx(options);
}

xnote.showAjaxDialog = function(title, url, buttons, functions) {
    $.get(url, function (resp) {
        var options = {};
        options.title = title;
        options.buttons = buttons;
        options.functions = functions;
        options.html = resp;
        var index = xnote.showDialogEx(options);
        // 刷新各种组件的默认值
        xnote.refresh();
    }).fail(function (error) {
        xnote.alert("调用接口失败，请重试");
    })
}

// 询问函数，原生prompt的替代方案
xnote.prompt = function(title, defaultValue, callback) {
    if (layer && layer.prompt) {
        // 使用layer弹层
        layer.prompt({
            title: title,
            value: defaultValue,
            scrollbar: false,
            area: ['400px', '300px']
        },
        function(value, index, element) {
            callback(value);
            layer.close(index);
        })
    } else {
        var result = prompt(title, defaultValue);
        callback(result);
    }
};

// 确认函数
xnote.confirm = function(message, callback) {
    if (layer && layer.confirm) {
        layer.confirm(message,
        function(index) {
            callback(true);
            layer.close(index);
        })
    } else {
        var result = confirm(message);
        callback(result);
    }
};

// 警告函数
xnote.alert = function(message) {
    if (layer && layer.alert) {
        layer.alert(message);
    } else {
        alert(message);
    }
};

xnote.toast = function (message, time) {
    if (layer && layer.msg) {
        layer.msg(message, {time: time});
    } else {
        myToast(message, time);
    }
}

var myToast = function(message, timeout) {
    if (timeout == undefined) {
        timeout = 1000;
    }
    var maxWidth = $(document.body).width();
    var maxHeight = $(document.body).height()
    var fontSize = 14;
    var toast = $("<div>").css({
        "margin": "0 auto",
        "position": "fixed",
        "left": 0,
        "top": "24px",
        "font-size": fontSize,
        "padding": "14px 18px",
        "border-radius": "4px",
        "background": "#000",
        "opacity": 0.7,
        "color": "#fff",
        "line-height": "22px",
        "z-index": 1000
    });
    toast.text(message);

    $(document.body).append(toast);

    // 宽度
    var width = toast.outerWidth();
    var left = (maxWidth - width) / 2;
    if (left < 0) {
        left = 0;
    }
    toast.css("left", left);

    // 高度
    var height = toast.outerHeight();
    var top = (maxHeight - height) / 2;
    if (top < 0) {
        top = 0;
    }
    toast.css("top", top);

    setTimeout(function() {
        toast.remove();
    }, timeout);
}

// 兼容之前的方法
window.showToast = window.xnote.toast;

/**
 * 展示选项对话框
 */
xnote.showOptionDialog = function (option) {
    var content = option.html;
    if (option.title === undefined) {
        option.title = false;
    }

    var oldStyle = $("body").css("overflow");
    $("body").css("overflow", "hidden");

    function recoveryStyle() {
        $("body").css("overflow", oldStyle);
    }

    var dialogIndex = layer.open({
        title: option.title,
        closeBtn: false,
        shadeClose: true,
        btn: [],
        content: content,
        skin: "x-option-dialog",
        yes: function (index, layero) {
            layer.close(index);
            // 恢复样式
            recoveryStyle();
        },
        cancel: function() {
            layer.close(index);
            // 恢复样式
            recoveryStyle();
        }
    });

    // 原组件点遮罩关闭没有回调事件，要重新一下
    $('#layui-layer-shade'+ dialogIndex).on('click', function(){
        console.log("xnote.showOptionDialog: shadowClose event")
        layer.close(dialogIndex);
        recoveryStyle();
    });
}

// 老版本的对话框，先保留在这里
window.ContentDialog = {
  open: function (title, content, size) {
    var width = $(".root").width() - 40;
    var area;

    if (isMobile()) {
      area = ['100%', '100%'];
    } else {
      if (size == "small") {
        area = ['400px', '300px'];        
      } else {
        area = [width + 'px', '80%'];
      }
    }

    layer.open({
      type: 1,
      shadeClose: true,
      title: title,
      area: area,
      content: content,
      scrollbar: false
    });
  }
}

xnote.closeAllDialog = function() {
    layer.closeAll();
}


// 自定义的dialog
$(function () {

    // 点击激活对话框的按钮
    $("body").on("click", ".dialog-btn", function() {
        var dialogUrl = $(this).attr("dialog-url");
        var dialogId = $(this).attr("dialog-id");
        var dailogTitle = $(this).attr("dialog-title");
        var optionSelector = $(this).attr("dialog-option-selector");
        if (dialogUrl) {
            // 通过新的HTML页面获取dialog
            $.get(dialogUrl, function(respHtml) {

                // 展示对话框
                xnote.showDialog(dailogTitle, respHtml);

                // 重新绑定事件
                xnote.fire("init-default-value");
            })
        } else if (optionSelector) {
            var html = $(optionSelector).html();
            var option = {};
            option.html = html;
            xnote.showOptionDialog(option);
        } else {
            xnote.alert("请定义[dialog-url]或者[dialog-option-selector]属性");
        }
    });


    /**
     * 初始化弹层
     */
    function initDialog() {
        // 初始化样式
        $(".x-dialog-close").css({
            "background-color": "red",
            "float": "right"
        });

        $(".x-dialog").each(function(index, ele) {
            var self = $(ele);
            var width = window.innerWidth;
            if (width < 600) {
                dialogWidth = width - 40;
            } else {
                dialogWidth = 600;
            }
            var top = Math.max((getWindowHeight() - self.height()) / 2, 0);
            var left = (width - dialogWidth) / 2;
            self.css({
                "width": dialogWidth,
                "left": left
            }).css("top", top);
        });

        $("body").css("overflow", "hidden");
    }

    /** 隐藏弹层 **/
    function onDialogHide() {
        $(".x-dialog").hide();
        $(".x-dialog-background").hide();
        $(".x-dialog-remote").remove(); // 清空远程的dialog
        $("body").css("overflow", "auto");
    }

    $(".x-dialog-background").click(function() {
        onDialogHide();
    });

    $(".x-dialog-close, .x-dialog-cancel").click(function() {
        onDialogHide();
    });

    function doModal(id) {
        initDialog();
        $(".x-dialog-background").show();
        $(".x-dialog-remote").show();
        $("#" + id).show();
    }

    xnote.initDialog = initDialog;
});
