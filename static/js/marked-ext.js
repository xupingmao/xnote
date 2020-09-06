/**
 * marked.js 插件扩展
 */
(function (window) {

    // marked 初始化操作
    var myRenderer = new marked.Renderer();
    myRenderer.headings = []

    marked.setOptions({
        renderer: myRenderer,
        highlight: highlight
    });
    
    marked.showMenu = true;
    var oldParse = marked.parse;

    // 后面都是定义的函数和重写html生成
    function escape(html, encode) {
      return html
        .replace(!encode ? /&(?!#?\w+;)/g : /&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    function highlight_csv (code) {
        try {
            // var csv = new CSV(code);
            var rows = CSV.parse(code);
            // console.log(rows);
            var table = $("<table>");
            for (var i = 0; i < rows.length; i++) {
                var col = rows[i];
                var tr = $("<tr>");
                for (var j = 0; j < col.length; j++) {
                    var td = $("<td>").html(col[j]);
                    tr.append(td);
                }
                table.append(tr);
            }
            console.log(table);
            window.csv_table = table;
            return "<table class='table'>" + table.html() + "</table>";
        } catch (e) {
            console.log(e);
            return escape(code);
        }
    }

    function replaceKeyword(html, regexp, target) {
        target = target || regexp;
        return html.replace(new RegExp(regexp, 'g'), '<code class="keyword">' + target + "</code>");
    }

    function highlightKeywords(code) {
        // 先简单处理一下
        var html = escape(code);
        /*
        var keywords = ["import ", "from ", "def ", "if ", "for ", "try:", "except:", "except ", 
            " in ", "not ", "return "];
        for (var i = 0; i < keywords.length; i++) {
            html = replaceKeyword(html, keywords[i]);
        }
        */
        return html;
    }

    function highlight (code, lang) {
        console.log(code, lang);
        if (lang) {
            lang = lang.toUpperCase();
        }
        if (lang == "CSV") {
            return highlight_csv(code);
        } else if (lang=="EXCEL") {
            code = code.replace(/\t/g, ",");
            // some \t may be replaced by four space
            code = code.replace(/ {4}/g, ',');
            console.log(code);
            return highlight_csv(code);
        } else {
            return highlightKeywords(code);
        }
    }

    function processCheckbox(text) {
        var result = {};
        if (/^\[\]/.test(text)) {
            result.checkbox = '<input type="checkbox" disabled="true"/>';
            result.text = '<span class="xnote-todo">' + text.substring(2) + '</span>';
        } else if (/^\[ \]/.test(text)) {
            result.checkbox = '<input type="checkbox" disabled="true"/>';
            result.text = text.substring(3);
        } else if (/^\[[Xx]\]/.test(text)) {
            result.checkbox = '<input type="checkbox" checked disabled="true"/>';
            result.text = '<span class="xnote-done">' + text.substring(3) + '</span>';
        } else {
            result.checkbox = '';
            result.text = text;
        }
        return result;
    }

    myRenderer.listitem = function (text) {
        var result = processCheckbox(text);
        return '<li>' + result.checkbox + result.text + '</li>\n';
    }

    myRenderer.paragraph = function (text) {
        var result = processCheckbox(text);
        return '<p>' + result.checkbox + result.text + '</p>\n';
    }

    myRenderer.heading = function (text, level, raw) {
        var id = raw.replace(/ /g, '-');
        this.headings.push({text:raw, link:id, level:level});
        var checkboxResult = processCheckbox(text);

        return '<h'
            + level
            + ' id="'
            + this.options.headerPrefix
            + id
            + '" class="marked-heading">'
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
    myRenderer.image = function(href, title, text) {
      var out = '<p class="marked-img"><img class="x-photo" src="' + href + '" alt="' + text + '" style="max-width:100%;"';
      if (title) {
        out += ' title="' + title + '"';
      }
      out += this.options.xhtml ? '/>' : '>';
      out += '</p>'
      return out;
    };

    // 重写code
    myRenderer.code = function(code, lang, escaped) {
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
    myRenderer.codespan = function(text) {
        return '<code class="marked-codespan">' + text + '</code>';
    }

    // 重写strong
    myRenderer.strong = function (text) {
        return '<strong class="marked-strong"><a href="/s/' + text + '">' + text + '</a></strong>';
    }

    myRenderer.table = function(header, body) {
      return '<table class="table">\n'
        + '<thead>\n'
        + header
        + '</thead>\n'
        + '<tbody>\n'
        + body
        + '</tbody>\n'
        + '</table>\n';
    };

    myRenderer.link = function(href, title, text) {
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

    function generateMenuHtml(myRenderer) {
        var menuText = '<div class="marked-contents">';
        
        menuText+="<ul>";
        for (var i = 0; i < myRenderer.headings.length; i++) {
            var heading = myRenderer.headings[i];
            var text = heading.text;
            var link = heading.link;
            var level = heading.level - 1;
            var margin_left = level * 10 + "px";
            var contentIndex = i + 1;
            menuText += '<li><a href="#link" style="margin-left:mleft">text</a></li>'.replace(/mleft|link|text/g, function (match, index) {
                // console.log(match, index);
                if (match == "link") {
                    // 目录的链接
                    return link;
                } else if (match == "mleft") {
                    // 处理缩进
                    return margin_left;
                } else {
                    // 目录的文本
                    return text;
                }
            });
        }
        menuText += "</ul></div>";
        return menuText;
    }

    marked.parse = function (text) {
        if (!marked.showMenu) {
            return oldParse(text);
        }
        
        myRenderer.headings = [];
        var outtext = oldParse(text);
        if (myRenderer.headings.length==0) {
            return outtext;
        }

        // 处理目录
        var menuHtml = generateMenuHtml(myRenderer);
        // outtext = menuHtml + outtext;

        $(".menu-aside").show();
        $("#menuBox").html(menuHtml);
        return outtext;
    }

})(window);
