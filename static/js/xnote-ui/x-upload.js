/**
 * xnote的公有方法
 */

var BASE_URL = "/static/lib/webuploader";

function createXnoteLoading() {
    return loadingIndex = layer.load(2);
}

function closeXnoteLoading(index) {
    layer.close(index);
}

xnote._initUploadEvent = function(uploader, fileSelector, successFn) {
    // 加载进度条索引
    var loadingIndex = 0;

    // 当有文件添加进来的时候
    uploader.on( 'fileQueued', function( file ) {
        // 接受文件
    });


    // 文件上传过程中创建进度条实时显示。
    uploader.on( 'uploadProgress', function( file, percentage ) {
        var percent = (percentage * 100).toFixed(2) + '%';
        console.log('upload process ' + percent)
    });

    uploader.on( 'uploadBeforeSend', function (object, data, headers) {
        $( '#uploadProgress' ).find('.progress').remove();
        data.dirname = "auto";
    })

    // 文件上传成功，给item添加成功class, 用样式标记上传成功。
    uploader.on( 'uploadSuccess', function( file, resp) {
        layer.close(loadingIndex);
        successFn(resp);
    });

    // 文件上传失败，显示上传出错。
    uploader.on( 'uploadError', function( file ) {
        console.error("uploadError", file);
        layer.close(loadingIndex);
        layer.alert('上传失败');
    });

    // 完成上传完了，成功或者失败，先删除进度条。
    uploader.on( 'uploadComplete', function( file ) {
        
    });

    // 监听文件上传事件
    $(fileSelector).on("change", function (event) {
        console.log(event);
        var fileList = event.target.files; //获取文件对象 
        if (fileList && fileList.length > 0) {
            loadingIndex = layer.load(2);
            uploader.addFile(fileList);
        }
    });
};

xnote.createUploader = function(fileSelector, chunked, successFn) {
    var req = {
        fileSelector: fileSelector,
        chunked: chunked,
        successFn: successFn,
        fixOrientation: true
    }

    if (chunked) {
        req.fixOrientation = false;
    }

    return xnote.createUploaderEx(req);
}

/** 创建上传器 **/
xnote.createUploaderEx = function(req) {
    var fileSelector = req.fileSelector;
    var chunked = req.chunked;
    var successFn = req.successFn;
    var fixOrientation = req.fixOrientation;


    if (fileSelector == undefined) {
        fileSelector = '#filePicker';
    }

    var upload_service;
    var serverHome = xnote.config.serverHome;

    // 默认分片
    if (chunked == undefined) {
        chunked = false;
    }

    if (chunked) {
        upload_service = serverHome + "/fs_upload/range";
    } else {
        // 不分片的上传服务
        upload_service = serverHome + "/fs_upload";
    }

    var uploader = WebUploader.create({
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
        threads: 1,
        // 是否保留header信息
        preserveHeaders: true,
        // 默认压缩是开启的
        // compress: {}
    });

    uploader.on('uploadBeforeSend', function(object, data, headers) {
        // web-uploader在上传文件的时候会自动进行旋转，但是不处理extif
        data.fix_orientation = fixOrientation;
    });

    if (successFn) {
        xnote._initUploadEvent(uploader, fileSelector, successFn);
    }

    return uploader;
};

// 把blob对象转换成文件上传到服务器
xnote.uploadBlob = function(blob, prefix, successFn, errorFn) {
    var fd = new FormData();
    // 加载页，用户阻止用户交互
    var loadingIndex = createXnoteLoading();

    fd.append("file", blob);
    fd.append("prefix", prefix);
    fd.append("name", "auto");
    //创建XMLHttpRequest对象
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/fs_upload');
    xhr.onload = function() {
        closeXnoteLoading(loadingIndex);
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
                if (errorFn) {
                    errorFn(xhr);
                }
            }
        };
    };

    xhr.onerror = function(error) {
        console.log(xhr.statusText);
        closeXnoteLoading(loadingIndex);
        if (errorFn) {
            errorFn(error)
        }
    }
    xhr.send(fd);
};

xnote.requestUpload = function(fileSelector, chunked, successFn, errorFn) {
    if (fileSelector == undefined) {
        throw new Error("selector is undefined");
    }

    var loadingIndex = 0;
    var uploader = window.xnote.createUploader(fileSelector, chunked);

    // 当有文件添加进来的时候
    uploader.on('fileQueued', function(file) {
        // 添加文件
        console.log("file = " + file);
    });

    // 文件上传过程中创建进度条实时显示。
    uploader.on('uploadProgress', function(file, percentage) {
        // 进度条
    });

    uploader.on('uploadBeforeSend', function(object, data, headers) {
        data.dirname = "auto";
    });

    // 文件上传成功，给item添加成功class, 用样式标记上传成功。
    uploader.on('uploadSuccess', function(file, resp) {
        console.log("uploadSuccess", file, resp);

        // 关闭加载页
        closeXnoteLoading(loadingIndex);
        // 回调成功函数
        successFn(resp);
    });

    // 文件上传失败，显示上传出错。
    uploader.on('uploadError', function(file) {
        layer.alert('上传失败');
        // 关闭加载页
        closeXnoteLoading(loadingIndex);
    });

    // 完成上传完了，成功或者失败，先删除进度条。
    uploader.on('uploadComplete', function(file) {
        console.log("uploadComplete", typeof(file), file);
    });

    // 触发上传文件操作
    $(fileSelector).click();

    // 选择文件完毕
    $(fileSelector).on("change", function(event) {
        console.log(event);
        var fileList = event.target.files; //获取文件对象 
        if (fileList && fileList.length > 0) {
            uploader.addFile(fileList);
            // 创建加载页，阻止用户操作
            loadingIndex = createXnoteLoading();
        }
        // 清空文件列表，不然下次上传会重复
        event.target.files = [];
    });
};

// 通过剪切板请求上传
// @param {event} e 粘贴事件
// @param {string} filePrefix 保存的文件名前缀
// @param {function} successFn 成功的回调函数
// @param {function} errorFn 失败的回调函数
window.xnote.requestUploadByClip = function (e, filePrefix, successFn, errorFn) {
    console.log(e);
    var clipboardData = e.clipboardData || e.originalEvent 
        && e.originalEvent.clipboardData || {};

    // console.log(clipboardData);
    if (clipboardData.items) {
        items = clipboardData.items;
        for (var index = 0; index < items.length; index++) {
            var item  = items[index];
            var value = item.value;
            // console.log("requestUploadByClip", item, value);
            if (/image/i.test(item.type)) {
                console.log(item);

                // 取消默认的粘贴动作（默认会粘贴文本）
                e.preventDefault();

                // 创建加载页，阻止用户操作
                var loadingIndex = createXnoteLoading();

                var blob = item.getAsFile();
                xnote.uploadBlob(blob, filePrefix, function (resp) {
                    successFn(resp);
                    closeXnoteLoading(loadingIndex);
                }, function (resp) {
                    if (errorFn) {
                        errorFn(resp);
                    }
                    closeXnoteLoading(loadingIndex);
                });
            }
        }
    }
}

/** x-upload.js end **/
