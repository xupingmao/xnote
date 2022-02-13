// 上传功能实现
// 已废弃: 请查看x-upload.js
(function (window) {
    // check whether browser support HTML5 file API

    var uploaded = {};

    if (!window.FileReader) {
        return;
    }

    function handleFiles(files) {
        if (files.length) {
            var file = files[0];
            var reader = new FileReader();
            reader.onload = function () {
                document.getElementById("filecontent").innerHTML = this.result;
            };
            reader.readAsText(file);
        }
    }

    /**
     * 使用HTML5 文件API上传文件
     * @param fileButtonId
     * @param fileName
     * @param uploadUrl
     * @param successCallback
     */
    function uploadFile(fileButtonId, uploadUrl, successCallback) {
        var files = document.getElementById(fileButtonId).files;
        if (files == undefined || files.length == 0) {
            return;
        }
        var fd = new FormData();
        fd.append("file", files[0]);
        fd.append("type", "html5")
        var xhr = new XMLHttpRequest();
        xhr.upload.addEventListener("progress", uploadProgress, false);
        
        var _onComplete = function (evt) {
            console.log(evt);
            if (successCallback) {
                successCallback(evt);
            } else {
                uploadComplete(evt);
            }
        }

        function wrapper(event) {
            
        }

        xhr.addEventListener("load", _onComplete, false);
        xhr.addEventListener("error", uploadFailed, false);
        xhr.addEventListener("abort", uploadCanceled, false);
        xhr.open("POST", uploadUrl);
        xhr.send(fd);
    }

    function uploadProgress(evt) {
        var elements = document.getElementsByClassName("upload-progress");
        if (elements.length > 0) {
            var element = elements[0];
        } else {
            return;
        }
        if (evt.lengthComputable) {
            var percentComplete = Math.round(evt.loaded * 100 / evt.total);
            element.innerHTML = "进度: " + percentComplete.toString() + '%';
        }
        else {
            element.innerHTML = 'unable to compute';
        }
    }

    function uploadComplete(evt) {
        /* This event is raised when the server send back a response */
        // alert(evt.target.responseText);
        console.log(evt);
        var responseText = evt.target.responseText;
        document.getElementById("progressNumber").innerHTML = "上传成功";
    }

    function uploadFailed(evt) {
        alert("There was an error attempting to upload the file.");
    }

    function uploadCanceled(evt) {
        alert("The upload has been canceled by the user or the browser dropped the connection.");
    }

    

    function uploadWithFileReader(files) {
        var reader = new FileReader();
        reader.onload = function (event) {
            console.log(event);
            var result = event.target.result;

            // console.log(result.length)
            console.log(event.target.result);
            console.log(result.byteLength);
        }

        reader.readAsArrayBuffer(files[0]);
        // var fd = new FormData();
        // fd.append(fileName, document.getElementById(fileButtonId).files[0]);
        // fd.append("type", "html5")
        // var xhr = new XMLHttpRequest();
        // xhr.upload.addEventListener("progress", uploadProgress, false);
        
        // var _onComplete = uploadComplete;

        // if (successCallback) {
        //     _onComplete = successCallback;
        // }

        // xhr.addEventListener("load", _onComplete, false);
        // xhr.addEventListener("error", uploadFailed, false);
        // xhr.addEventListener("abort", uploadCanceled, false);
        // xhr.open("POST", uploadUrl);
        // xhr.send(fd);
    }

    // 导出上传接口
    window.uploadFile = uploadFile;
    window.uploadWithFileReader = uploadWithFileReader;

})(window);