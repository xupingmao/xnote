if (window.xnote == undefined) {
    window.xnote = {};
}

window.xnote.showDialog = function(title, html) {
    if (isMobile()) {
        var area = ['100%', '100%'];
    } else {
        var area = ['600px', '80%'];
    }

    return layer.open({
        type: 1,
        title: title,
        shadeClose: true,
        area: area,
        content: html,
        scrollbar: false
    });
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

window.xnote.toast = function(message, time) {
    if (time == undefined) {
        time = 1000;
    }
    var maxWidth = $(document.body).width();
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
    var width = toast.outerWidth();
    var left = (maxWidth - width) / 2;
    if (left < 0) {
        left = 0;
    }
    toast.css("left", left);
    setTimeout(function() {
        toast.remove();
    },
    time);
}

// 兼容之前的方法
window.showToast = window.xnote.toast;


// 自定义的dialog
$(function () {
    // 点击激活对话框的按钮
    $(".dialog-btn").click(function() {
        var dialogUrl = $(this).attr("dialog-url");
        var dialogId = $(this).attr("dialog-id");
        if (dialogUrl) {
            // 通过新的HTML页面获取dialog
            $.get(dialogUrl, function(respHtml) {
                $(document.body).append(respHtml);
                doModal(dialogId);
                // 重新绑定事件
                xnote.fire("init-default-value");
                $(".x-dialog-close, .x-dialog-cancel").unbind("click");
                $(".x-dialog-close, .x-dialog-cancel").on("click",
                function() {
                    onDialogHide();
                });
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

});
