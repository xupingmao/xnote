(function () {

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
            return escape(code);
        }
    }

    var myRenderer = new marked.Renderer();
    myRenderer.headings = []

    function processCheckbox(text) {
        var result = {};
        if (/^\[\]/.test(text)) {
            result.checkbox = '<input type="checkbox" disabled="true"/>';
            result.text = text.substring(2);
        } else if (/^\[ \]/.test(text)) {
            result.checkbox = '<input type="checkbox" disabled="true"/>';
            result.text = text.substring(3);
        } else if (/^\[[Xx]\]/.test(text)) {
            result.checkbox = '<input type="checkbox" checked disabled="true"/>';
            // result.checkbox = '<img src="/static/image/checked.png" style="height:1.5rem;">';
            result.text = text.substring(3);
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
    myRenderer.heading = function (text, level, raw) {
        var id = raw.replace(/ /g, '-');
        this.headings.push({text:raw, link:id, level:level});
        var checkboxResult = processCheckbox(text);

        return '<h'
            + level
            + ' id="'
            + this.options.headerPrefix
            // 对中文无效
            // + raw.toLowerCase().replace(/[^\w]+/g, '-')
            + id
            // + '">'
            + '" class="marked-heading">'
            + checkboxResult.checkbox
            + checkboxResult.text
            + '</h'
            + level
            + '>\n';

    }

    // 重写img
    myRenderer.image = function(href, title, text) {
      var out = '<img src="' + href + '" alt="' + text + '" style="max-width:100%;"';
      if (title) {
        out += ' title="' + title + '"';
      }
      out += this.options.xhtml ? '/>' : '>';
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
        return '<pre class="marked-pre"><code>'
          + (escaped ? code : escape(code, true))
          + '\n</code></pre>';
      }

      return '<pre class="marked-pre"><code class="'
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
        var menuText = "<h1>目录</h1>";
        menuText+="<ol>";
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
        menuText+="</ol>";
        outtext = menuText + outtext;
        return outtext;
    }

})();
