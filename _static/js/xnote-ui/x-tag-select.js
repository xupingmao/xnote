/** x-tag-select.js
 * 表单的 tag 风格选择器（DataForm 的 tag_select 行），依赖jQuery
 *
 * DOM 结构（由 FormRow.render_tag_select 渲染）:
 *   <div class="form-tag-select" data-multiple="true|false">
 *       <input type="hidden" name="field" value="1,2">
 *       <span class="tag lightblue" data-value="1">标签1</span>
 *       ...
 *   </div>
 *
 * 值的唯一来源是隐藏域，选中态（active类）只用于展示。
 * 注意: 本文件是运行时代码，必须兼容ES3语法。
 */

if (!xnote.initTagSelect) {

    // 把选中标签的 data-value 按DOM顺序同步到隐藏域
    function syncTagSelectValue($box) {
        var values = [];
        $box.find(".tag.active").each(function (index, ele) {
            values.push($(ele).attr("data-value"));
        });
        $box.find("input[type=hidden]").val(values.join(","));
    }

    xnote.handleTagSelectClick = function (target) {
        var $tag = $(target).closest(".tag[data-value]");
        if ($tag.length == 0) {
            return;
        }
        var $box = $tag.closest(".form-tag-select");

        // 只读: 不响应点击
        if ($box.attr("data-readonly")) {
            return;
        }

        // 单选: 先清掉同组其他标签的选中态
        if ($box.attr("data-multiple") == "false") {
            $box.find(".tag.active").not($tag).removeClass("active");
        }

        $tag.toggleClass("active");
        syncTagSelectValue($box);
    };

    xnote.initTagSelect = function (root) {
        if (root === undefined) {
            root = document;
        }
        // 通过data-bind标记避免重复绑定
        $(root).find(".form-tag-select").each(function (index, ele) {
            var $box = $(ele);
            if ($box.attr("data-tag-select-bind")) {
                return;
            }
            $box.attr("data-tag-select-bind", "1");

            // 事件委托到 .tag 上：点到容器空白处不会误触发
            $box.delegate(".tag[data-value]", "click", function (event) {
                xnote.handleTagSelectClick(event.currentTarget);
            });

            // 以服务端渲染的隐藏域为准，修正选中态（例如value里有非法值）
            var values = ($box.find("input[type=hidden]").val() || "").split(",");
            $box.find(".tag[data-value]").each(function (i, tag) {
                var $tag = $(tag);
                if (values.indexOf($tag.attr("data-value")) >= 0) {
                    $tag.addClass("active");
                } else {
                    $tag.removeClass("active");
                }
            });
        });
    };
}
