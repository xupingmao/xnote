/**
 * 模板渲染器
 * @author xupingmao
 * @since 2021/05/01 14:56:59
 * @modified 2022/01/09 16:42:27
 * @filename x-template.js
 */


/**
 * 简单的模板渲染，这里假设传进来的参数已经进行了html转义
 * <code>
 *   var text = xnote.renderTemplate("Hello,{name}!", {name: "World"});
 *   // text = "Hello,World";
 * </code>
 */
xnote.renderTemplate = function(templateText, object) {
    return templateText.replace(/\$\{(.*?)\}/g, function (context, objKey) {
        return object[objKey.trim()] || '';
    });
};
