/**
 * 模板渲染器
 * @author xupingmao
 * @since 2021/05/01 14:56:59
 * @modified 2022/01/09 16:42:27
 * @filename x-template.js
 */


/**
 * 简单的模板渲染，这里假设传进来的参数已经进行了html转义
 * @param {string} templateText 模板字符串
 * @param {object} object 参数
 * 
 * <code>
 *   var text = xnote.renderTemplate("Hello,${name}!", {name: "World"});
 *   // text = "Hello,World";
 * </code>
 */
xnote.renderTemplate = function(templateText, object) {
    function escapeHTML(text) {
        if (text === undefined || text === "") {
            return text;
        }
        var temp = document.createElement("div");
        temp.innerHTML = text;
        return temp.innerText || temp.textContent
    }

    // TODO 处理转义问题（基于 ${key} 的简单占位符替换，不依赖 art-template）
    return templateText.replace(/\$\{(.+?)\}/g, function (context, objKey) {
        var value = object[objKey.trim()];
        return escapeHTML(value);
    });
};

xnote.string.format = xnote.renderTemplate;


