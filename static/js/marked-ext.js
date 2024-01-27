/**
 * marked.js 插件扩展
 * 依赖: marked.js/jquery
 */
(function (window) {

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
        menuText += "</ul>";
        menuText += "</div>";

        console.log("contents.generateHtml end");
        return menuText;
    }

    // 全局变量
    var globals = {
        contents: new MarkedContents()
    };

    // marked 初始化操作
    var myRenderer = new marked.Renderer();

    myRenderer.headings = [];

    marked.setOptions({
        renderer: myRenderer,
        highlight: highlight
    });

    marked.showMenu = true;
    var oldParse = marked.parse;

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
            var rows = CSV.parse(code);
            var table = $("<table>").attr("data-index", dupIndex).addClass("table");
            var editAction = $("<a>").text("编辑表格");
            editAction.attr("onclick", extOptions.csvEditFunc + "(this)");
            editAction.attr("data-code", code).attr("data-index", dupIndex);
            editAction.attr("data-lang", lang);

            if (rows.length > 0) {
                var headRow = rows[0];
                var head = $("<tr>");
                for (var j = 0; j < headRow.length; j++) {
                    var th = $("<th>").text(getCsvRowText(headRow[j]));
                    head.append(th);
                }
                table.append(head);

                for (var i = 1; i < rows.length; i++) {
                    var row = rows[i];
                    var tr = $("<tr>");
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

    function replaceKeyword(html, regexp, target) {
        target = target || regexp;
        return html.replace(new RegExp(regexp, 'g'), '<code class="keyword">' + target + "</code>");
    }

    function highlightKeywords(code, lang) {
        // 这个需要依赖 hightlight
        console.log("code language:", lang);
        if (window.hljs == undefined) {
            return code
        }
        if (lang == undefined) {
            return hljs.highlightAuto(code).value;
        }
        try {
            return hljs.highlight(code, { language: lang }).value;
        } catch (e) {
            return hljs.highlightAuto(code).value;
        }
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
            return highlightKeywords(code, langUpper);
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

        var checkbox = $("<input>")
            .attr("type", "checkbox")
            .addClass("marked")
            .attr("data-text", text);

        if (disabled) {
            checkbox.attr("disabled", true);
        }

        // 调试日志
        console.info(extOptions.checkboxIndex, checkbox);
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

        this.headings.push({ text: raw, link: id, level: level });
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

    /// 重写img, 不依赖JS版本
    // myRenderer.image = function(href, title, text) {
    //   var out = '<p class="marked-img"><a href="' + href + '"><img src="' + href + '" alt="' + text + '" style="max-width:100%;"';
    //   if (title) {
    //     out += ' title="' + title + '"';
    //   }
    //   out += this.options.xhtml ? '/>' : '>';
    //   out += '</a></p>'
    //   return out;
    // };

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
        if ("csv" == lang.toLowerCase()) {
            return '<div>' + code + '</div>';
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
        return '<code class="marked-codespan">' + text + '</code>';
    }

    // 重写strong
    myRenderer.strong = function (text) {
        return '<strong class="marked-strong"><a href="/s/' + text + '">' + text + '</a></strong>';
    }

    // 重写html标签
    myRenderer.html = function (html) {
        try {
            var cap = marked.Lexer.rules.html.exec(html);
            console.log(cap, html);
            var htmlTag = cap[1].toLowerCase();
            if (htmlTag == "script" || htmlTag == "pre") {
                // 过滤脚本
                return "";
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
        var out = '<a target="_blank" href="' + href + '"';
        // var out = '<a href="' + href + '" target="_blank" ';
        if (title) {
            out += ' title="' + title + '"';
        }
        out += '>' + text + '</a>';
        return out;
    };

    function buildMenuLink(text, link) {
        return '<li><a href="#link">text</a></li>'.replace(/mleft|link|text/g, function (match, index) {
            // console.log(match, index);
            if (match == "link") {
                // 目录的链接
                return link;
            } else {
                // 目录的文本
                return text;
            }
        });
    }

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

    // 重写parse方法
    marked.parse = function (text) {
        if (!marked.showMenu) {
            return oldParse(text);
        }

        myRenderer.headings = [];
        var outtext = oldParse(text);
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

    marked.parseAndRender = function (text, target, options) {
        // 处理扩展选项
        extOptions = initExtOptions(options);
        extOptions.text = text;

        var html = marked.parse(text);
        $(target).html(html);
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
