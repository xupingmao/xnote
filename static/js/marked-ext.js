/**
 * marked.js 插件扩展
 */
(function (window) {

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

    function replace_keyword(html, regexp, target) {
        target = target || regexp;
        return html.replace(new RegExp(regexp, 'g'), '<code class="keyword">' + target + "</code>");
    }

    function highlight_keywords(code) {
        // 先简单处理一下
        var html = escape(code);
        /*
        var keywords = ["import ", "from ", "def ", "if ", "for ", "try:", "except:", "except ", 
            " in ", "not ", "return "];
        for (var i = 0; i < keywords.length; i++) {
            html = replace_keyword(html, keywords[i]);
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
            return highlight_keywords(code);
        }
    }

    var myRenderer = new marked.Renderer();
    myRenderer.headings = []

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

      if (!lang) {
        return '<pre class="marked-code"><code>'
          + (escaped ? code : escape(code, true))
          + '\n</code></pre>';
      }

      return '<pre class="marked-code"><code class="'
        + this.options.langPrefix
        + escape(lang, true)
        + '">'
        + (escaped ? code : escape(code, true))
        + '\n</code></pre>\n';
    };

    // 重写strong
    myRenderer.strong = function (text) {
        return '<strong class="marked-strong">' + text + '</strong>';
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

    marked.setOptions({
        renderer: myRenderer,
        highlight: highlight
    });
    var oldParse = marked.parse;

    marked.showMenu = true;

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
        var menuText = '<div class="marked-contents"><h1>目录</h1>';
        menuText+="<ul>";
        for (var i = 0; i < myRenderer.headings.length; i++) {
            var heading = myRenderer.headings[i];
            var text = heading.text;
            var link = heading.link;
            var level = heading.level;
            var margin_left = level * 10 + "px";
            menuText += '<li><a href="#link" style="margin-left:mleft">text</a></li>'.replace(/mleft|link|text/g, function (match, index) {
                // console.log(match, index);
                if (match == "link") {
                    return link;
                } else if (match == "mleft") {
                    return margin_left;
                } else {
                    return text;
                }
            });
        }
        menuText+="</ul></div>";
        outtext = menuText + outtext;
        return outtext;
    }

})(window);
