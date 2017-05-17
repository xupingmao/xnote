(function (window) {
    // check whether browser support HTML5 file API

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
     */
    function uploadFile(fileButtonId, fileName, uploadUrl) {
        var fd = new FormData();
        fd.append(fileName, document.getElementById(fileButtonId).files[0]);
        fd.append("type", "html5")
        var xhr = new XMLHttpRequest();
        xhr.upload.addEventListener("progress", uploadProgress, false);
        xhr.addEventListener("load", uploadComplete, false);
        xhr.addEventListener("error", uploadFailed, false);
        xhr.addEventListener("abort", uploadCanceled, false);
        xhr.open("POST", uploadUrl);
        xhr.send(fd);
    }

    function uploadProgress(evt) {
        if (evt.lengthComputable) {
            var percentComplete = Math.round(evt.loaded * 100 / evt.total);
            document.getElementById('progressNumber').innerHTML = "进度: " + percentComplete.toString() + '%';
        }
        else {
            document.getElementById('progressNumber').innerHTML = 'unable to compute';
        }
    }

    function uploadComplete(evt) {
        /* This event is raised when the server send back a response */
        // alert(evt.target.responseText);
        var responseText = evt.target.responseText;
        document.getElementById("resultLink").innerHTML = "上传成功";
    }

    function uploadFailed(evt) {
        alert("There was an error attempting to upload the file.");
    }

    function uploadCanceled(evt) {
        alert("The upload has been canceled by the user or the browser dropped the connection.");
    }

    // 导出上传接口
    window.uploadFile = uploadFile;

})(window);