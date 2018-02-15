// @author xupingmao
// @since 2018/02/13
// @modified 2018/02/15 11:05:27


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

    if (options.mode) {
        mode = options.mode;
    }

    var editor = CodeMirror.fromTextArea($(selector)[0], {
        lineNumbers: true,
        mode: mode,
        indentUnit:4,
        lineWrapping: true
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