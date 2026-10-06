/**
 * x-form.js — 表单组件（DataForm / PageEditForm / QueryForm / DialogForm）的前端逻辑
 *
 * 历史: 这些逻辑原先内联在 xnote_handlers/common/form/form.html 的 <script> 里,
 * 但弹窗是通过 html 注入的, 注入的 <script> 不会执行, 弹窗表单因此拿不到上传/日期
 * 等交互。现在统一挪到 xnote-ui, 由 xnote.initForm() 在页面加载与弹窗渲染后初始化。
 *
 * 后端参数（提交地址 / model / action / 删除后跳转）通过 <form> 上的 data-* 传递,
 * 不再由模板变量拼进 JS, 这样同一份 JS 可以服务页面上任意多个表单。
 *
 * DOM 约定:
 *   <form class="x-form"
 *         data-form-path="/xxx" data-model-name="message" data-save-action="save"
 *         data-delete-reload-href="/xxx">
 *   <input data-oninput-ajax-url="/xxx"> 值变化时发 ajax, 返回的 data 交给
 *         xnote.executeCommands 执行（后端用 webutil.CommandItem 构造命令）
 *
 * 依赖: jQuery / xnote.http / xnote.executeCommands / xnote.layout / xnote.createUploaderEx
 * 注意: 本文件是运行时代码, 必须兼容ES3语法。
 */

if (xnote.form === undefined) {
    xnote.form = {};
}

// oninput 触发 ajax 的防抖时间（毫秒），避免每敲一个字符就请求一次
xnote.form.onInputDelay = 300;

// 后端约定的“返回上一页”标记
// 注意: xnote_code_builder 会把行内的 // 当成注释截掉，URL 里的 // 必须拆开拼接
xnote.form.BACK_URL = "internal:" + "/" + "/back";

/**
 * 表单里的图片/文件上传组件交互（与评论、随手记上传交互一致）
 * 命名保持 formUpload：上传模板里的 onclick 直接引用它
 */
if (!xnote.formUpload) {
    xnote.formUpload = {
        pick: function (pickerId) {
            $(pickerId).click();
        },
        addItem: function (rowEl, webpath, kind) {
            var name = webpath.split("/").pop();
            var $row = $(rowEl);
            var $list = $row.find(".form-upload-preview");
            if (kind == "image") {
                var div = $("<div>").addClass("form-upload-thumb").attr("data-src", webpath);
                var img = $("<img>").attr("src", webpath + "?mode=thumbnail").attr("data-src", webpath);
                var del = $("<a>").addClass("form-upload-del")
                    .attr("onclick", "xnote.formUpload.removeItem(this)").text("删除");
                div.append(img).append(del);
                $list.append(div);
            } else {
                var div = $("<div>").addClass("form-upload-file").attr("data-src", webpath);
                var link = $("<a>").attr("href", webpath).attr("target", "_blank").text(name);
                var del = $("<a>").addClass("form-upload-del")
                    .attr("onclick", "xnote.formUpload.removeItem(this)").text("删除");
                div.append(link).append(del);
                $list.append(div);
            }
            xnote.formUpload.syncValue($row);
        },
        removeItem: function (target) {
            var $item = $(target).closest("[data-src]");
            var $row = $item.closest(".form-upload-row");
            $item.remove();
            xnote.formUpload.syncValue($row);
        },
        syncValue: function ($row) {
            var values = [];
            // 只统计每个附件的容器节点（.form-upload-thumb / .form-upload-file）,
            // 其内部 <img> 也带 data-src, 若一并统计会导致同一附件被重复计数
            $row.find(".form-upload-thumb, .form-upload-file").each(function (index, ele) {
                values.push($(ele).attr("data-src"));
            });
            $row.find("input[type=hidden][name]").val(values.join(","));
        }
    };
}

/**
 *  WebUploader 未随全局打包加载时（如弹窗表单），动态引入后再初始化
 */
xnote.form.ensureWebUploader = function (callback) {
    if (typeof WebUploader !== "undefined") {
        callback();
        return;
    }
    // 避免同一页面多个表单重复加载脚本
    if (xnote._webuploader_loading) {
        var timer = setInterval(function () {
            if (typeof WebUploader !== "undefined") {
                clearInterval(timer);
                callback();
            }
        }, 50);
        return;
    }
    xnote._webuploader_loading = true;

    var serverHome = xnote.config.serverHome;
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.type = "text/css";
    link.href = serverHome + "/_static/lib/webuploader/webuploader.css";
    document.head.appendChild(link);

    var script = document.createElement("script");
    script.src = serverHome + "/_static/lib/webuploader/webuploader.nolog.min.js";
    script.onload = function () {
        xnote._webuploader_loading = false;
        callback();
    };
    script.onerror = function () {
        xnote._webuploader_loading = false;
        xnote.alert("上传组件加载失败");
    };
    document.head.appendChild(script);
};

/**
 * 初始化表单内的图片/文件上传组件（依赖 WebUploader，按需动态加载）
 */
xnote.form.initUploaders = function ($form) {
    var $rows = $form.find(".form-upload-row");
    if ($rows.length == 0) {
        return;
    }

    var initRows = function () {
        $rows.each(function (index, ele) {
            var $row = $(ele);
            var kind = $row.attr("data-upload-kind");
            var picker = $row.attr("data-picker");
            xnote.createUploaderEx({
                fileSelector: picker,
                chunked: false,
                successFn: function (resp) {
                    xnote.formUpload.addItem($row, resp.webpath, kind);
                },
                fixOrientation: true,
                fileName: "auto"
            });
        });
    };

    xnote.form.ensureWebUploader(initRows);
};

/**
 * 自动调整 textarea 的高度（随输入内容变化）
 */
xnote.form.initTextarea = function ($form) {
    if (!xnote.layout.initAutoResizeTextarea) {
        return;
    }
    $form.find("textarea").each(function (index, ele) {
        var $elem = $(ele);
        // 同一个 textarea 只初始化一次，避免重复绑定 input 事件
        if ($elem.attr("data-autoresize-bind")) {
            return;
        }
        $elem.attr("data-autoresize-bind", "1");
        xnote.layout.initAutoResizeTextarea(ele);
    });
};

/**
 * 日期控件：点击时渲染 laydate（同一个元素只渲染一次）
 */
xnote.form.initDateInput = function ($form) {
    $form.find(".form-date").each(function (index, ele) {
        var $elem = $(ele);
        if ($elem.attr("data-laydate-bind")) {
            return;
        }
        $elem.attr("data-laydate-bind", "true");

        $elem.click(function (event) {
            var elem = event.target;
            laydate.render({
                elem: elem,
                type: $(elem).attr("data-date-type"),
                change: function (value, date, endDate) {
                    // 数据变化就更新
                    $(elem).val(value);
                    // laydate 是js赋值，不会触发input事件，这里手动触发一次，
                    // 让 data-oninput-ajax-url 之类的回调能收到变化
                    $(elem).trigger("input");
                    // 自动关闭日期选择器
                    $(elem).remove(".layui-date");
                },
                show: true
            });
        });
    });
};

/**
 * 值变化就发 ajax，返回的 data 交给 xnote.executeCommands 执行
 * 对应 FormRow.oninput_ajax_url（渲染成 data-oninput-ajax-url）
 */
xnote.form.requestOnInputAjax = function ($input, url) {
    var params = {};
    params.name = $input.attr("name");
    params.value = $input.val();

    xnote.http.post(url, params, function (resp) {
        if (resp.success) {
            if (resp.data) {
                xnote.executeCommands(resp.data);
            }
        } else {
            xnote.toast(resp.message);
        }
    });
};

/**
 * 绑定 oninput 的 ajax 回调
 */
xnote.form.initOnInputAjax = function ($form) {
    $form.find("[data-oninput-ajax-url]").each(function (index, ele) {
        var $input = $(ele);
        if ($input.attr("data-oninput-bind")) {
            return;
        }
        $input.attr("data-oninput-bind", "1");

        var url = $input.attr("data-oninput-ajax-url");
        if (!url) {
            return;
        }

        // select 没有 input 事件，用 change
        var eventName = $input.is("select") ? "change" : "input";
        var timer = null;

        $input.on(eventName, function () {
            if (timer) {
                clearTimeout(timer);
            }
            timer = setTimeout(function () {
                timer = null;
                xnote.form.requestOnInputAjax($input, url);
            }, xnote.form.onInputDelay);
        });
    });
};

/**
 * 初始化页面里的表单
 * @param {Object|string} root 可选，表单所在的容器（DOM / 选择器 / jQuery对象），默认整个文档
 */
xnote.initForm = function (root) {
    if (root === undefined) {
        root = document;
    }

    $(root).find(".x-form").each(function (index, ele) {
        var $form = $(ele);
        // 通过data-form-bind标记避免重复初始化
        if ($form.attr("data-form-bind")) {
            return;
        }
        $form.attr("data-form-bind", "1");

        xnote.form.initOnInputAjax($form);
        xnote.form.initTextarea($form);
        xnote.form.initDateInput($form);
        xnote.form.initUploaders($form);
    });
};

/**
 * 取按钮（data-form-id）对应的表单
 */
xnote.form.findForm = function (target) {
    var formId = $(target).attr("data-form-id");
    if (!formId) {
        return $();
    }
    return $("#" + formId);
};

xnote.submitFormSave = function (target) {
    var $form = xnote.form.findForm(target);
    if ($form.length == 0) {
        xnote.alert("表单不存在");
        return;
    }

    var request = {};
    request.data = JSON.stringify($form.formData());

    var saveURL = $form.attr("data-form-path")
        + "?model=" + $form.attr("data-model-name")
        + "&action=" + $form.attr("data-save-action");

    xnote.http.post(saveURL, request, function (resp) {
        if (resp.success) {
            xnote.toast("保存成功");
            setTimeout(function () {
                if (resp.redirect_url) {
                    if (resp.redirect_url == xnote.form.BACK_URL) {
                        history.back();
                    } else {
                        window.location.href = resp.redirect_url;
                    }
                } else {
                    window.location.reload();
                }
            }, 500);
        } else {
            xnote.toast(resp.message);
        }
    });
};

xnote.submitFormDelete = function (target) {
    var $form = xnote.form.findForm(target);
    if ($form.length == 0) {
        xnote.alert("表单不存在");
        return;
    }

    var confirmMsg = $(target).attr("data-message");
    var deletePostURL = $(target).attr("data-url");

    if (deletePostURL == "") {
        xnote.alert("delete_url is empty");
        return;
    }

    var callback = function () {
        var request = {};
        request.data = JSON.stringify($form.formData());

        xnote.http.post(deletePostURL, request, function (resp) {
            if (resp.success) {
                xnote.toast("删除成功");
                setTimeout(function () {
                    window.location.href = $form.attr("data-delete-reload-href");
                }, 500);
            } else {
                xnote.toast(resp.message);
            }
        });
    };

    xnote.confirm(confirmMsg, callback);
};

// 别名
xnote.handleFormSubmit = xnote.submitFormSave;

xnote.submitFormQuery = function (target) {
    var $form = xnote.form.findForm(target);
    $form.submit();
};

$(function () {
    // 页面里的表单（弹窗里的表单由 xnote.refresh -> initDefaultValue 触发）
    xnote.initForm();
});
