/**
 * xnote的公有方法
 */
var BASE_URL = "/static/lib/webuploader";

if (window.xnote == undefined) {
    window.xnote = {};
}

/** 创建上传器 **/
window.xnote.createUploader = function(fileSelector, chunked) {
    if (fileSelector == undefined) {
        fileSelector = '#filePicker';
    }

    var upload_service;

    // 默认分片
    if (chunked == undefined) {
        chunked = false;
    }

    if (chunked) {
        upload_service = "/fs_upload/range";
    } else {
        // 不分片的上传服务
        upload_service = "/fs_upload";
    }

    return WebUploader.create({
        // 选完文件后，是否自动上传。
        auto: true,
        // swf文件路径
        swf: BASE_URL + '/Uploader.swf',
        // 文件接收服务端。
        server: upload_service,
        // 选择文件的按钮。可选。
        // 内部根据当前运行是创建，可能是input元素，也可能是flash.
        pick: fileSelector,
        // 需要分片
        chunked: chunked,
        // 默认5M
        // chunkSize: 1024 * 1024 * 5,
        chunkSize: 1024 * 1024 * 5,
        // 重试次数
        chunkRetry: 10,
        // 文件上传域的name
        fileVal: "file",
        // 不开启并发
        threads: 1
        // 默认压缩是开启的
        // compress: {}
    });
};

// 把blob对象转换成文件上传到服务器
window.xnote.uploadBlob = function(blob, prefix, successFn, errorFn) {
    var fd = new FormData();
    fd.append("file", blob);
    fd.append("prefix", prefix);
    fd.append("name", "auto");
    //创建XMLHttpRequest对象
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/fs_upload');
    xhr.onload = function() {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                var data = JSON.parse(xhr.responseText);
                if (successFn) {
                    successFn(data);
                } else {
                    console.log(data);
                }
            } else {
                console.error(xhr.statusText);
            }
        };
    };
    xhr.onerror = function(e) {
        console.log(xhr.statusText);
    }
    xhr.send(fd);
};

window.xnote.requestUpload = function(fileSelector, chunked, successFn, errorFn) {
    if (fileSelector == undefined) {
        throw new Error("selector is undefined");
    }

    var loadingIndex = 0;
    var uploader = window.xnote.createUploader(fileSelector, chunked);

    // 当有文件添加进来的时候
    uploader.on('fileQueued',
    function(file) {
        // 添加文件
        console.log("file = " + file);
    });

    // 文件上传过程中创建进度条实时显示。
    uploader.on('uploadProgress',
    function(file, percentage) {
        // 进度条
    });

    uploader.on('uploadBeforeSend',
    function(object, data, headers) {
        data.dirname = "auto";
    })

    // 文件上传成功，给item添加成功class, 用样式标记上传成功。
    uploader.on('uploadSuccess',
    function(file, resp) {
        console.log("uploadSuccess", file, resp);

        layer.close(loadingIndex);

        successFn(resp);
    });

    // 文件上传失败，显示上传出错。
    uploader.on('uploadError',
    function(file) {
        layer.alert('上传失败');
        layer.close(loadingIndex);
    });

    // 完成上传完了，成功或者失败，先删除进度条。
    uploader.on('uploadComplete',
    function(file) {
        console.log("uploadComplete", typeof(file), file);
    });

    // 触发上传文件操作
    $(fileSelector).click();

    // 选择文件完毕
    $(fileSelector).on("change",
    function(event) {
        console.log(event);
        var fileList = event.target.files; //获取文件对象 
        if (fileList && fileList.length > 0) {
            uploader.addFile(fileList);
            loadingIndex = layer.load(2);
        }
        // 清空文件列表，不然下次上传会重复
        event.target.files = [];
    });
};

/** x-upload.js end **/
