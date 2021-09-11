if (window.xnote == undefined) {
    window.xnote = {};
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

window.xnote.showDialogEx = function (options) {
    var area = getDialogArea();
    var title = options.title;
    var html  = options.html;
    var buttons = options.buttons;
    var functions = options.functions;
    var anim = options.anim;

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
            area: area,
            content: html,
            anim: anim,
            scrollbar: false
        });
    } else {
        return layer.open({
            type: 1,
            title: title,
            shadeClose: true,
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

window.xnote.showDialog = function(title, html, buttons, functions) {
    var options = {};
    options.title = title;
    options.html  = html;
    options.buttons = buttons;
    options.functions = functions;
    return xnote.showDialogEx(options);
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

window.xnote.toast = function (message, time) {
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


// 自定义的dialog
$(function () {
    // 点击激活对话框的按钮
    $(".dialog-btn").click(function() {
        var dialogUrl = $(this).attr("dialog-url");
        var dialogId = $(this).attr("dialog-id");
        var dailogTitle = $(this).attr("dialog-title");
        if (dialogUrl) {
            // 通过新的HTML页面获取dialog
            $.get(dialogUrl, function(respHtml) {

                // 展示对话框
                xnote.showDialog(dailogTitle, respHtml);

                // 重新绑定事件
                xnote.fire("init-default-value");
            })
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

    /**
   * 隐藏弹层
   */
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

window.xnote.closeAllDialog = function() {
    layer.closeAll();
}

