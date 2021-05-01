/**
 * description here
 * @author xupingmao
 * @since 2021/05/01 14:56:59
 * @modified 2021/05/01 15:17:19
 * @filename x-template.js
 */

if (window.xnote == undefined) {
    window.xnote = {};
}

(function (xnote) {
    /**
     * 简单的模板渲染，这里假设传进来的参数已经进行了html转义
     */
    function renderTemplate(templateText, object) {
        return templateText.replace(/\$\{(.*?)\}/g, function (context, objKey) {
            return object[objKey.trim()] || '';
        });
    }

    xnote.renderTemplate = renderTemplate;

})(window.xnote);