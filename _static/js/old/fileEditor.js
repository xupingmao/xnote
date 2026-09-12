var editor = new TagEditor("related", "{{file.related}}",  "|", "relatedTags");
editor.setUpperCase(true);

function copy(obj) {
    var newObj;
    if (obj instanceof Array) {
        newObj = [];
    } else {
        newObj = {};
    }
    for (var key in obj) {
        newObj[key] = obj[key];
    }
    return newObj;
}

function updateRelated() {
    var result = document.getElementById("relatedTags");
    var text = result.value;
    tags = text;
    var result = ajaxGet("/file?option=updateRelated&id={{file.id}}&value="+tags, function (result) {
        // alert(result);
        var resultObj = JSON.parse(result);
        if (resultObj.success) {
            var resultSpan = document.getElementById("result");
            resultSpan.innerHTML = "success!";
            setTimeout(function () {
                resultSpan.innerHTML = "";
            }, 1000);
        } else {
            alert("update fail, e = " + result.msg);
        }
    }, function (e) { alert ("send message failed!!!"); })
}

function delLink() {
    var r = confirm("del {{file.name}}?");
    if (r) {
        location.href="/file?option=del&id={{file.id}}";
    }
}
var opts = {
    container: "epiceditor",
    textarea: "fileContent",
    basePath: '/lib/epiceditor/',
    clientSideStorage: false,
    localStorageName: null,
    useNativeFullscreen: true,
    parser: marked,
    file: {
        name: 'lib',
        defaultContent: '',
        autoSave: false
    },
    theme: {
        base: 'themes/base/epiceditor.css',
        preview: 'themes/preview/preview-dark.css',
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
var related = "{{file.related}}";
if (related.indexOf("MD") >=0 ) {
    var editor = new EpicEditor(opts);
    editor.load();
    var viewerOpts = copy(opts);
    viewerOpts.container = "viewer";
    var viewer = new EpicEditor(viewerOpts);
    viewer.load();
    viewer.preview();
} else {
    var textContainer = document.getElementById("fileContent");
    textContainer.style.display = "block";
}