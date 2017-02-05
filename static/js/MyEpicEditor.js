/**
 * require jquery, CSV.js
 */
(function (window) {
    window.MyEpicEditor = function (divContainer, textContainer) {

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
                return "<table>" + table.html() + "</table>";
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
                code = code.replace(/\t/gi, ",");
                // some \t may be replaced by four space
                code = code.replace(/    /gi, ',');
                return highlight_csv(code);
            } else {
                return escape(code);
            }
        }

        // set marked code highlight function
        marked.defaults.highlight = highlight;

        var opts = {
            container: divContainer,
            textarea: textContainer,
            basePath: '/lib/epiceditor/',
            clientSideStorage: false,
            localStorageName: null,
            useNativeFullscreen: false,
            parser: marked,
            file: {
                name: 'lib',
                defaultContent: '',
                autoSave: false
            },
            theme: {
                base: 'themes/base/epiceditor.css',
                preview: 'themes/preview/github.css',
                editor: 'themes/editor/epic-dark.css'
            },
            button: {
                preview: true,
                fullscreen: true,
                bar: "auto"
            },
            focusOnLoad: false,
            shortcut: {
                modifier: 18,
                fullscreen: 70,
                preview: 80
            },
            string: {
                togglePreview: 'Toggle Preview Mode',
                toggleEdit: 'Toggle Edit Mode',
                toggleFullscreen: 'Enter Fullscreen'
            },
            autogrow: true
        }
        var proto = new EpicEditor(opts);
        // inheritance
        for (var name in proto) {
            this[name] = proto[name];
        }
    }
    
}) (window)