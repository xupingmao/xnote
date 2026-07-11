/**
 * marked.js 插件扩展
 * 依赖: marked.js/jquery
 */

var markedConfig = {
    showMenu: true,
    // 是否展示时间线、评论区之类的系统组件菜单
    showSystemContents: true,
    // 是否展示CSV表格的序号列
    showTableNo: true,
    // CSV表格的序号列宽度
    csvTableNoWidth: 50
};

(function (window) {
    var gHeadingToLinkMap = {};


    // 目录生成
    function MarkedContents() {
        this.id = 0;
    }

    function initExtOptions(options) {
        if (options === undefined) {
            options = {
                text: "",
                hideMenu: false,
                checkboxIndexMap: {},
                checkboxIndex: 0,
                csvIndex: 0,
                csvIndexMap: {},
                csvEditFunc: "alert"
            };
        }
        if (options.checkboxIndexMap === undefined) {
            options.checkboxIndexMap = {};
        }
        if (options.checkboxIndex === undefined) {
            options.checkboxIndex = 0;
        }
        if (options.csvIndex === undefined) {
            options.csvIndex = 0;
        }
        if (options.csvIndexMap === undefined) {
            options.csvIndexMap = {};
        }
        if (options.csvEditFunc === undefined) {
            options.csvEditFunc = "alert";
        }
        return options; 
    }

    MarkedContents.prototype.createNewId = function () {
        this.id++;
        return "heading-" + this.id;
    }

    MarkedContents.prototype.generateHtml = function (myRenderer) {
        if (extOptions.hideMenu) {
            return ""
        }

        console.log("contents.generateHtml start");

        var menuText = "";
        var menuList = [];
        var minLevel = null;
        var prevLevel = 1;

        menuText += '<div class="marked-contents">';
        menuText += '<span class="marked-contents-title">目录</span>';
        menuText += "<ul>";

        // 先把基础层级计算好
        // level从1开始
        for (var i = 0; i < myRenderer.headings.length; i++) {
            var heading = myRenderer.headings[i];
            var text = heading.text;
            var link = heading.link;
            var level = heading.level;

            if (minLevel === null) {
                minLevel = level;
            } else {
                minLevel = Math.min(minLevel, level);
            }

            menuList.push([level, text, link]);
        }

        if (minLevel === null) {
            minLevel = 1;
        }

        if (markedConfig.showSystemContents) {
            menuList.push([minLevel, "事件时间线", "#events-timeline"])
            menuList.push([minLevel, "评论区", "#note-comments"])
        }

        console.log("contents minLevel:", minLevel);

        // 准备渲染目录
        for (var i = 0; i < menuList.length; i++) {
            var item = menuList[i];
            var level = item[0];
            var text = item[1];
            var link = item[2];

            // 调整层级
            level = level - minLevel + 1;

            if (level === prevLevel) {
                menuText += buildMenuLink(text, link);
            }

            if (level > prevLevel) {
                // 进入下一层
                menuText += repeatElement("<ul>", level - prevLevel);
                menuText += buildMenuLink(text, link);
            }

            if (level < prevLevel) {
                // 退出下一层
                menuText += repeatElement("</ul>", prevLevel - level);
                menuText += buildMenuLink(text, link);
            }

            // 更新之前的层级
            prevLevel = level;
        }

        menuText += repeatElement("</ul>", prevLevel);
        menuText += "</div>";
        
        console.log("contents.generateHtml end");
        return menuText;
    }

    // 全局变量
    var globals = {
        contents: new MarkedContents()
    };

    
    /**
     * @typedef { import('../lib/marked/marked.js') }
     */
    // marked 初始化操作
    var myRenderer = new marked.Renderer();

    myRenderer.headings = [];

    marked.setOptions({
        renderer: myRenderer,
        highlight: highlight,
        // 换行替换成<br>
        breaks: true
    });

    markedConfig.showMenu = true;
    var originalParse = marked.parse;
    var newEscapeRegexp = /^\\([\\`*{}\[\]#+\-.!_>])/;
    // 不对 \( 和 \) 进行转义
    marked.InlineLexer.rules.escape = newEscapeRegexp;
    marked.InlineLexer.rules.gfm.escape = newEscapeRegexp;
    
    // text 移除了反斜杠的终止符号
    // var originalTextRegexp = marked.InlineLexer.rules.text;
    // var newTextRegexp = /^[\s\S]+?(?=[<!\[_*`]| {2,}\n|$)/;
    // marked.InlineLexer.rules.text = newTextRegexp;
    // marked.InlineLexer.rules.gfm.text = newTextRegexp;


    // 扩展选项
    var extOptions = initExtOptions();

    // 进度的正则匹配
    var regexPercent = /\d+(\.\d+)?\%/;

    // 后面都是定义的函数和重写html生成
    function escape(html, encode) {
        return html
            .replace(!encode ? /&(?!#?\w+;)/g : /&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function getCsvRowText(text) {
        if (text === undefined) {
            return "-";
        }
        return text;
    }

    function highlightCsv(code, lang) {
        // 处理csv的展示
        extOptions.csvIndex++;
        var dupIndex = extOptions.csvIndexMap[code]
        if (dupIndex === undefined) {
            dupIndex = 0;
        } else {
            dupIndex++;
        }
        extOptions.csvIndexMap[code] = dupIndex;

        var codeBlock = "```" + lang + "\n" + code + "\n```";

        try {
            // var csv = new CSV(code);
            var rows = CSV.parse(code, {cast: false});
            var table = $("<table>").attr("data-index", dupIndex).addClass("table csv-table");
            var editAction = $("<a>").text("[编辑表格]");
            editAction.attr("onclick", extOptions.csvEditFunc + "(this)");
            editAction.attr("data-code", code).attr("data-index", dupIndex);
            editAction.attr("data-lang", lang);

            if (rows.length > 0) {
                var headRow = rows[0];
                var head = $("<tr>");

                if (markedConfig.showTableNo) {
                    var noTh = $("<th>").text("序号").css("min-width", markedConfig.csvTableNoWidth + "px");
                    head.append(noTh);
                }

                for (var j = 0; j < headRow.length; j++) {
                    var thText = getCsvRowText(headRow[j]);
                    var th = $("<th>");
                    var thContent = $("<span>").text(thText);
                    var copyLink = $("<a>").text("[复制]").css("margin-left", "5px").css("font-size", "12px");
                    copyLink.attr("onclick", "xnote.copyCsvColumn(this, " + j + ")");
                    th.append(thContent).append(copyLink);
                    head.append(th);
                }
                table.append(head);
                
                for (var i = 1; i < rows.length; i++) {
                    var row = rows[i];
                    var tr = $("<tr>");

                    if (markedConfig.showTableNo) {
                        var noTd = $("<td>").text(i);
                        tr.append(noTd);
                    }
                    
                    for (var j = 0; j < row.length; j++) {
                        var td = $("<td>").text(getCsvRowText(row[j]));
                        tr.append(td);
                    }
                    table.append(tr);
                }
            }
            console.log(table);
            window.csv_table = table;

            if (extOptions.text.indexOf(codeBlock) >= 0) {
                // 符合csv标准格式, 返回编辑按钮
                return editAction.prop("outerHTML") + table.prop("outerHTML");
            }

            return table.prop("outerHTML");
        } catch (e) {
            console.log(e);
            return escape(code);
        }
    }

    xnote.copyCsvColumn = function(element, columnIndex) {
        var table = $(element).closest("table");
        var rows = table.find("tr");
        var columnData = [];
        
        // 收集表头
        var headerRow = rows.first();
        var headerCells = headerRow.find("th");
        if (markedConfig.showTableNo) {
            columnData.push(headerCells.eq(columnIndex + 1).find("span").text());
        } else {
            columnData.push(headerCells.eq(columnIndex).find("span").text());
        }
        
        // 收集数据行
        for (var i = 1; i < rows.length; i++) {
            var row = rows.eq(i);
            var cells = row.find("td");
            if (markedConfig.showTableNo) {
                columnData.push(cells.eq(columnIndex + 1).text());
            } else {
                columnData.push(cells.eq(columnIndex).text());
            }
        }
        
        // 复制到剪贴板
        var textToCopy = columnData.join("\n");
        navigator.clipboard.writeText(textToCopy).then(function() {
            // 可以添加一个提示，告知用户复制成功
            xnote.toast("列数据已复制到剪贴板");
        }).catch(function(err) {
            xnote.alert("复制失败:", err);
        });
    }



    function highlight(code, lang) {
        console.log(code, lang);
        var langUpper;
        if (lang) {
            langUpper = lang.toUpperCase();
        }
        if (langUpper == "CSV") {
            return highlightCsv(code, lang);
        } else if (langUpper == "EXCEL") {
            code = code.replace(/\t/g, ",");
            // some \t may be replaced by four space
            code = code.replace(/ {4}/g, ',');
            console.log(code);
            return highlightCsv(code, lang);
        } else {
            // 实现逻辑在 editor.js 文件
            return xnote.editor.highlightCodeBlock(code, langUpper);
        }
    }

    function katexRender(content) {
        if (window.katex) {
            try {
                var result = katex.renderToString(content, { displayMode: false });
            } catch {
                var result = myRenderer.codespan("解析失败:" + content);
            }
            // console.debug("katex render", content, "result", result);
            return result
        } else {
            return content;
        }
    }

    function getMarkdownText(content) {
        if (/<[^>]+>/g.test(content)) {
            // contains tag
            var contentLi = $("<li>" + content + "</li>");
            var newContent = "";
            var contents = contentLi.contents();
            var hasError = false;
            for (var i = 0; i < contents.length; i++) {
                var item = contents[i];
                if (item.nodeName === "#text") {
                    newContent += item.textContent;
                } else if (item.tagName == "CODE") {
                    newContent += "`" + item.textContent + "`";
                } else {
                    console.debug("unknown element:", item);
                    hasError = true;
                    break;
                }
            };
            if (hasError) {
                return content;
            } else {
                return newContent;
            }
        } else {
            return content;
        }
    }

    // 处理待办的样式
    function processCheckbox(text, clickable) {
        var result = {};
        var disabled = false;

        if (clickable !== undefined) {
            disabled = !clickable;
        }

        // 多选框选项索引
        extOptions.checkboxIndex++;

        var dataText = getMarkdownText(text);

        var checkbox = $("<input>")
            .attr("type", "checkbox")
            .addClass("marked")
            .attr("data-text", dataText);

        if (disabled) {
            checkbox.attr("disabled", true);
        }

        // 调试日志
        console.debug("checkboxIndex", extOptions.checkboxIndex, checkbox);
        // 处理同名的待办索引
        var index = extOptions.checkboxIndexMap[text]
        if (index === undefined) {
            index = 0;
        } else {
            index++;
        }
        extOptions.checkboxIndexMap[text] = index;
        checkbox.attr("data-index", index); // 记录是第几个checkbox

        if (/^\[\]/.test(text)) {
            var content = text.substring(2);
            var tail = "";
            var parts = content.split("<ul>", 2); // content可能包含HTML
            if (parts.length == 2) {
                content = parts[0];
                tail = "<ul>" + parts[1];
            }

            var element = $("<span>").html(content).addClass("xnote-todo");

            if (regexPercent.test(content)) {
                // 包含百分比的加上进行中的进度
                element = element.addClass("doing");
            }
            result.checkbox = checkbox.prop("outerHTML");
            result.text = element.prop("outerHTML") + tail;
        } else if (/^\[ \]/.test(text)) {
            result.checkbox = checkbox.prop("outerHTML");
            result.text = text.substring(3);
        } else if (/^\[[Xx]\]/.test(text)) {
            checkbox.attr("checked", true);
            console.info("set checked", checkbox);
            result.checkbox = checkbox.prop("outerHTML");
            result.text = '<span class="xnote-done">' + text.substring(3) + '</span>';
        } else {
            result.checkbox = '';
            result.text = text;
        }
        return result;
    }

    myRenderer.listitem = function (text) {
        var result = processCheckbox(text, true);
        return '<li>' + result.checkbox + result.text + '</li>\n';
    }

    myRenderer.paragraph = function (text) {
        var result = processCheckbox(text);
        return '<p>' + result.checkbox + result.text + '</p>\n';
    }

    myRenderer.heading = function (text, level, raw) {
        var id = globals.contents.createNewId();

        this.headings.push({ text: raw, link: "#" + id, level: level });
        var checkboxResult = processCheckbox(text);

        return '<h'
            + level
            + ' id="'
            + this.options.headerPrefix
            + id
            + '" class="marked-heading"'
            + ' "data-level"=' + level
            + '>'
            + checkboxResult.checkbox
            + checkboxResult.text
            + '</h'
            + level
            + '>\n';
    }

    // 重写img
    myRenderer.image = function (href, title, text) {
        var imgSrc = href;
        // if (href && /^https?/.test(href)) {
        //     imgSrc = "/fs_cache/image?url=" + encodeURIComponent(href);
        // }
        var out = '<p class="marked-img"><img class="x-photo" src="' + imgSrc + '" alt="' + text + '" style="max-width:100%;"';
        if (title) {
            out += ' title="' + title + '"';
        }
        out += this.options.xhtml ? '/>' : '>';
        out += '</p>'
        return out;
    };

    // 重写code
    myRenderer.code = function (code, lang, escaped) {
        if (lang) {
            lang = lang.toLowerCase();

            if (lang === 'mermaid') {
                return '<pre class="mermaid">' + escape(code, true) + '</pre>';
            }
        }

        if (this.options.highlight) {
            var out = this.options.highlight(code, lang);
            if (out != null && out !== code) {
                escaped = true;
                code = out;
            }
        }

        // 没有定义语言
        if (!lang) {
            return '<pre class="marked-code"><code>'
                + (escaped ? code : escape(code, true))
                + '\n</code></pre>';
        }

        // csv
        if ("csv" === lang) {
            return '<div>' + code + '</div>';
        }

        if (lang === 'latex') {
            return katexRender(code);
        }

        // 定义语言
        return '<pre class="marked-code"><code class="'
            + this.options.langPrefix
            + escape(lang, true)
            + '">'
            + (escaped ? code : escape(code, true))
            + '\n</code></pre>\n';
    };

    // 单行的code
    myRenderer.codespan = function (text) {
        // text是escape之后的
        var element = $("<code>").html(text).addClass("marked-codespan");
        return element.prop("outerHTML");
    }

    // 重写strong
    myRenderer.strong = function (text) {
        return '<strong class="marked-strong"><a href="/s/' + text + '">' + text + '</a></strong>';
    }

    /**
     * 重写html标签
     * @param {string} html 
     * @returns {string}
     */
    myRenderer.html = function (html) {
        try {
            var cap = marked.Lexer.rules.html.exec(html);
            console.log(cap, html);
            var htmlTag = cap[1].toLowerCase();
            if (htmlTag == "script" || htmlTag == "pre") {
                // 过滤脚本
                return "";
            }
            if (htmlTag == "latex") {
                var content = $(html).text();
                return katexRender(content);
            }
        } catch (e) {
            console.error(e);
        }
        return html;
    }

    myRenderer.table = function (header, body) {
        return '<table class="table marked-table">\n'
            + '<thead>\n'
            + header
            + '</thead>\n'
            + '<tbody>\n'
            + body
            + '</tbody>\n'
            + '</table>\n';
    };

    myRenderer.link = function (href, title, text) {
        if (this.options.sanitize) {
            try {
                var prot = decodeURIComponent(unescape(href))
                    .replace(/[^\w:]/g, '')
                    .toLowerCase();
            } catch (e) {
                return '';
            }
            if (prot.indexOf('javascript:') === 0 || prot.indexOf('vbscript:') === 0) {
                return '';
            }
        }
        var out = '<a href="' + href + '"';
        if (href.startsWith("/") || href.startsWith("./")) {
            // internal link
        } else if (href.startsWith("#")) {
            // hash link
            out += ' data-link-type="hash"';
        } else {
            out += ' target="_blank"';
        }
        if (title) {
            out += ' title="' + title + '"';
        }
        out += '>' + text + '</a>';
        return out;
    };

    function formatMenuText(text) {
        if (text.startsWith("**") && text.endsWith("**")) {
            return text.substring(2, text.length - 2);
        } else {
            return text;
        }
    }

    function buildMenuLink(text, link) {
        gHeadingToLinkMap[text.toLowerCase()] = link;
        text = formatMenuText(text);
        return '<li><a href="link">text</a></li>'.replace(/mleft|link|text/g, function (match, index) {
            // console.log(match, index);
            if (match == "link") {
                // 目录的链接
                return link;
            } else {
                // 目录的文本
                return text;
            }
        });
    };

    function repeatElement(element, times) {
        var text = "";
        for (var i = 0; i < times; i++) {
            text += element;
        }
        return text;
    }

    function adjustTableWidth() {
        xnote.table.adjustWidth(".marked-table");
    }

    // 处理行内公式（用 \( \) 包裹）
    myRenderer.text = function(text) {
        // text 已经被转义了
        return text;
    };

    // 重写parse方法
    marked.parse = function (text) {
        // reset vars
        gHeadingToLinkMap = {};

        if (!markedConfig.showMenu) {
            return originalParse(text);
        }

        myRenderer.headings = [];
        var outtext = originalParse(text);
        if (myRenderer.headings.length == 0) {
            return outtext;
        }

        // 处理目录
        var menuHtml = globals.contents.generateHtml(myRenderer);

        outtext = menuHtml + outtext;

        $(".menu-aside").show();
        $("#menuBox").html(menuHtml);
        return outtext;
    };

    /**
     * 解析 Markdown 文本，将其分割为代码块和普通文本的 token 列表
     * @param {string} text - 输入的 Markdown 文本
     * @returns {Array<{type: string, text: string}>} - 包含 code 和 text 类型 token 的列表
     * @example
     * // 输入:
     * "普通文本\n\`\`\`js\n代码\n\`\`\`\n更多文本"
     * // 输出:
     * [
     *   { type: "text", text: "普通文本\n" },
     *   { type: "code", text: "\`\`\`js\n代码\n\`\`\`" },
     *   { type: "text", text: "\n更多文本" }
     * ]
     */
    function parseTextBlocks(text) {
        const tokens = [];
        let src = text.replace(/^ +$/gm, ''); // 参考 Lexer.prototype.token，移除行尾空格
        const codeBlockRegex = /(`{3,})([a-zA-Z0-9_-]*?)\n([\s\S]*?)\1/;
        
        while (src) {
            let cap;
            
            // 匹配代码块
            if (cap = codeBlockRegex.exec(src)) {
                // 添加代码块前的普通文本
                if (cap.index > 0) {
                    const textContent = src.substring(0, cap.index);
                    if (textContent.trim() !== '') {
                        tokens.push({ type: 'text', text: textContent });
                    }
                }
                
                // 添加代码块
                const codeContent = `${cap[1]}${cap[2]}\n${cap[3]}${cap[1]}`;
                tokens.push({ type: 'code', text: codeContent });
                
                // 从原文本中移除已匹配的代码块
                src = src.substring(cap.index + cap[0].length);
                continue;
            }
            
            // 剩余的普通文本
            if (src.trim() !== '') {
                tokens.push({ type: 'text', text: src });
            }
            break;
        }
        
        return tokens;
    }

    function preHandleBlock(block) {
        // 预处理：替换行内公式定界符
        // '\(' {公式内容} '\)'
        // '\[' {公式内容} '\]'
        // '$$' {块级公式} '$$'
        try {
            var replace_func = function(match, content) {
                return "<latex>" + content + "</latex>";
            }
            block = block.replace(/\\\(([\s\S]*?)\\\)/g, replace_func);
            block = block.replace(/\\\[([\s\S]*?)\\\]/g, replace_func);
            block = block.replace(/\$\$([\s\S]*?)\$\$/g, replace_func);  
            return block;
        } catch (e) {
            console.error("preHandleBlock failed:", e);
            return block;
        }
    }
    
    /**
     * @param {string} text 
     * @returns {string}
     */
    function preHandleText(text) {
        var result = "";
        var blocks = parseTextBlocks(text);
        for (var i = 0; i < blocks.length; i++) {
            var block = blocks[i];
            if (block.type == 'code') {
                result += block.text;
            } else {
                result += preHandleBlock(block.text);
            }
        }
        return result;
    }

    marked.parseAndRender = function (text, target, options) {
        // 预处理text文本
        text = preHandleText(text);
        // console.log("text=", text);
        // 处理扩展选项
        extOptions = initExtOptions(options);
        extOptions.text = text;

        var html = marked.parse(text);
        $(target).html(html);
        this.afterRender();
    };

    // 更新内链
    marked._updateHashLinks = function () {
        $("[data-link-type=hash]").each(function (index, ele) {
            var href = $(ele).attr("href");
            if (href.startsWith("#")) {
                var hrefHash = href.substring(1).toLowerCase();
                var linkId = gHeadingToLinkMap[hrefHash];
                if (linkId) {
                    $(ele).attr("href", linkId);
                }
            }
        })
    }

    // 更新latex公式
    marked._updateLatex = function () {
        $("latex").each(function (index, ele) {
            var content = $(ele).text();
            $(ele).html(katexRender(content));
        })
    }

    // 更新mermaid图表
    marked._updateMermaid = function () {
        if (window.mermaid) {
            mermaid.run();
        }
    }


    // 渲染后更新操作
    marked.afterRender = function () {
        this._updateHashLinks();
        this._updateLatex();
        this._updateMermaid();
        
        adjustTableWidth();

        // 注册点击事件
        $("input[type=checkbox].marked").click(function (e) {
            var onCheckboxClicked = extOptions.onCheckboxClicked;
            if (onCheckboxClicked) {
                onCheckboxClicked(e);
            }
        });
    };


})(window);
