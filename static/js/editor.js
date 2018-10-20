// @author xupingmao
// @since 2018/02/13
// @modified 2018/10/20 16:14:41


// var codeMirror = CodeMirror.fromTextArea(editor, {
//     lineNumbers: true,
//     mode: { name: "text/x-markdown", fencedCodeBlocks: true },
//     lineWrapping: true,
//     fixedGutter: true,
// });

// fixedGutter
// 设置gutter跟随编辑器内容水平滚动（false）还是固定在左侧（true或默认）

/**
 * 初始化codeMirror编辑器
 * @param {string} selector 选择器
 * @param {object} options 可选项
 */
function initCodeMirror(selector, options) {
    var mode = "text/x-sh";
    var name = options.filename || "";
    var height = options.height || "450px";
    var executable = false;

    if (name.endsWith(".py")) {
        mode = "text/x-python";
        // executable = true;
    }
    if (name.endsWith(".js")) {
        mode = "text/javascript";
    } 
    if (name.endsWith(".c")) {
        mode = "text/x-c";
    } 
    if (name.endsWith(".java")) {
        mode = "text/x-java";
    } 
    if (name.endsWith(".md")) {
        mode = "text/x-markdown";
    } 
    if (name.endsWith(".sh") || name.endsWith(".command")) {
        mode = "text/x-sh";
    } 
    if (name.endsWith(".php")) {
        mode = "text/x-php";
    }
    if (name.endsWith(".css")) {
        mode = "text/css";
    }

    if (options.mode) {
        mode = options.mode;
    }

    var keyMap = "default";

    if (CodeMirror.keyMap.sublime) {
        keyMap = "sublime";
    }

    var editor = CodeMirror.fromTextArea($(selector)[0], {
        lineNumbers: true,
        mode: mode,
        indentUnit:4,
        lineWrapping: true,
        keyMap: keyMap
    });
    editor.setSize("auto", height);
    editor.on("update", function (codeMirror, changeObj) {
        $(selector).val(codeMirror.doc.getValue());
    });
    // tab键处理
    editor.setOption("extraKeys", {
        Tab: function(cm) {
            if (cm.somethingSelected()) {
                cm.indentSelection('add');
            } else {            
                var spaces = Array(cm.getOption("indentUnit") + 1).join(" ");
                cm.replaceSelection(spaces);
            }
        }
    });


    if (mode == "text/x-python") {
        $("#execute").show();
        $("#execute").click(function (event) {
            var content = editor.doc.getValue();
            $.post("/system/command/python", 
                {content: content} ,
                function (responseText) {
                    var data = responseText;
                    $("#resultDiv").show();
                    $("#result").show().text(data.data);
                });
        })
    }
    return editor;
}


(function () {
    // TODO 处理CJK的宽度, CJK认为是2个字符宽度
    var _padding = '';
    for (var i = 0; i < 1000; i++) {
        _padding += ' ';
    }

    var _isMacOS = navigator.userAgent.indexOf("Mac OS") >= 0;
    function isMacOS() {
        return _isMacOS;
    }
    if (isMacOS()) {
        console.log("Mac OS");
    }

    String.prototype.padLeft = function (size, value) {
        // return _padding.substring(0, size-this.length) + this;
        var text = this;
        while (getStringWidth(text) < size) {
            text += value;
        }
        return text;
    }

    function getCharWidth(c) {
        if (!c) {
            return 0;
        }
        var code = c.charCodeAt(0);
        if (code > 127) {
            if (isMacOS()) {
                // Mac是个奇葩, 3个汉字5个宽度
                return 1.66;
            }
            return 2;
        }
        return 1;
    }

    function getStringWidth(str) {
        if (!str) {
            return 0;
        }
        var width = 0;
        for (var i = 0; i < str.length; i++) {
            width += getCharWidth(str[i]);
        }
        return Math.round(width);
    }

    function formatTable(text) {
        // var text = "name|age|comment\n---|----|--\nCheck No|001|Nothing\nHello中文02|002|中文";
        var lines = text.split('\n');
        var table = [];
        var colWidth = [];

        for (var i = 0; i < lines.length; i++) {
            var row = lines[i];
            var cols = row.split('|');
            table[i] = cols;
            for (var j = 0; j < cols.length; j++) {
                if (cols.length > 1) {                
                    var cell = cols[j].trim();
                    cols[j] = cell;
                    var width = colWidth[j] || 0;
                    colWidth[j] = Math.max(getStringWidth(cell), width);
                }
            }
        }
        console.log(colWidth);

        var newText = "";
        var newLines = [];

        for (var i = 0; i < table.length; i++) {
            var row = table[i];
            if (row.length > 1) {            
                for (var j = 0; j < row.length; j++) {
                    var cell = row[j].trim();
                    if (cell.indexOf('---') >= 0) {
                        row[j] = cell.padLeft(colWidth[j], '-');
                    } else {
                        row[j] = cell.padLeft(colWidth[j], ' ');
                    }
                    
                }
            }
            newLines.push(row.join('|'));
        }
        return newLines.join("\n");
    }

    window.formatMarkdownTable = formatTable;
    
})();