/**
 * JQuery 扩展
 * @author xupingmao
 * @since 2021/09/19 19:41:58
 * @modified 2021/09/19 19:51:35
 * @filename jq-ext.js
 */


/**
 * 获取表单数据
 */
$.fn.extend({
    "formData": function () {
        var data = {}
        $(this).find("[name]").each(function (index, element) {
            var key = $(element).attr("name");
            var value = $(element).val();
            data[key] = value;
        });

        return data;
    }
});
