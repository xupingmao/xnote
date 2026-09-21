/** x-switch.js
 * 通用的开关组件，依赖jQuery
 *
 * DOM 结构:
 *   <span class="x-switch active" data-on-value="true" data-off-value="false">
 *       <input type="hidden" name="field" value="true">
 *       <span class="switch-track"><span class="switch-dot"></span></span>
 *       <span class="switch-text">文本</span>
 *   </span>
 *
 * 值的唯一来源是隐藏域，active类只用于展示（与 x-tag-select.js 的契约一致），
 * 因此开关放到表单里提交时取到的是隐藏域的值，而不是原生checkbox的value。
 *
 * 注意: 本文件是运行时代码，必须兼容ES3语法。
 */

if (!xnote.initSwitch) {

    // 把选中态同步到隐藏域（值的唯一来源）
    function syncSwitchValue($box) {
        var $input = $box.find("input[type=hidden]");
        if ($input.length == 0) {
            return;
        }
        var isActive = $box.hasClass("active");
        $input.val(isActive ? $box.attr("data-on-value") : $box.attr("data-off-value"));
        $box.attr("aria-checked", isActive ? "true" : "false");
    }

    xnote.toggleSwitch = function (target) {
        var $box = $(target).closest(".x-switch");
        if ($box.length == 0) {
            return;
        }
        // 禁用状态不响应点击
        if ($box.hasClass("disabled") || $box.attr("data-disabled")) {
            return;
        }
        $box.toggleClass("active");
        syncSwitchValue($box);
    };

    xnote.initSwitch = function (root) {
        if (root === undefined) {
            root = document;
        }
        $(root).find(".x-switch").each(function (index, ele) {
            var $box = $(ele);
            // 通过data-bind标记避免重复绑定
            if ($box.attr("data-switch-bind")) {
                return;
            }
            $box.attr("data-switch-bind", "1");

            $box.bind("click", function (event) {
                xnote.toggleSwitch(event.currentTarget);
            });

            // 键盘操作（role=switch 的可访问性要求）：空格/回车切换
            $box.bind("keydown", function (event) {
                if (event.keyCode == 32 || event.keyCode == 13) {
                    event.preventDefault();
                    xnote.toggleSwitch(event.currentTarget);
                }
            });

            // 以服务端渲染的隐藏域为准，修正选中态
            var $input = $box.find("input[type=hidden]");
            if ($input.length > 0) {
                var value = $input.val();
                var onValue = $box.attr("data-on-value");
                if (value !== undefined && value !== null && String(value) == String(onValue)) {
                    $box.addClass("active");
                } else {
                    $box.removeClass("active");
                }
                syncSwitchValue($box);
            }
        });
    };
}
