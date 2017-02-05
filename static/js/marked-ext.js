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
    myRenderer.highlight = highlight;
    myRenderer.listitem = function (text) {
        if (/^\[\]/.test(text)) {
            return '<li><input type="checkbox" disabled="true"/>' + text.substring(2) + '</li>\n';
        } else if (/^\[[Xx]\]/.test(text)) {
            return '<li><input type="checkbox" checked disabled="true"/>' + text.substring(3) + '</li>\n';
        } else {
            return '<li>' + text + '</li>\n';
        }
    }
    myRenderer.heading = function (text, level, raw) {
        var id = raw.replace(/ /g, '-');
        this.headings.push({text:raw, link:id, level:level});
        return '<h'
            + level
            + ' id="'
            + this.options.headerPrefix
            // 对中文无效
            // + raw.toLowerCase().replace(/[^\w]+/g, '-')
            + id
            // + '">'
            + '" class="marked-heading">'
            + text
            + '</h'
            + level
            + '>\n';

    }
    marked.setOptions({
        renderer: myRenderer
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
        outtext = menuText + outtext;
        return outtext;
    }

})();
