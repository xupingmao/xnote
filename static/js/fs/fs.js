/**
 * 文件相关函数
 */
var FileView = {};
var FileAPI = {};

xnote.action.fs = FileView;
xnote.api.fs = FileAPI;

// 调用重命名的API
FileAPI.rename = function(dirname, oldName, newName, callback) {
    if (newName != oldName && newName) {
        xnote.http.post("/fs_api/rename", 
            {dirname: dirname, old_name: oldName, new_name: newName}, 
            function (resp) {
                if (resp.code == "success") {
                    callback(resp);
                } else {
                    xnote.alert("重命名失败:" + resp.message);
                }
        });
    } else {
        xnote.alert("请输入有效文件名");
    }
};


// 删除文件
FileView.delete = function(target) {
    var path = $(target).attr("data-path");
    var name = $(target).attr("data-name");
        
    xnote.confirm("确定删除【" + name + "】?", function (value) {
        xnote.http.post("/fs_api/remove", {path: path}, function (resp) {
            if (resp.code == "success") {
                window.location.reload();
            } else {
                xnote.alert("删除失败:" + resp.message);
            }
        });
    });
};

// 重命名
FileView.rename = function(target) {
    var filePath = $(target).attr("data-path");
    var oldName = $(target).attr("data-name");
    var realname = $(target).attr("data-realname");
    if (xnote.isEmpty(realname)) {
        realname = oldName;
    }

    var dirname = $("#currentDir").val();
    xnote.prompt("输入新的文件名", oldName, function (newName) {
        FileAPI.rename(dirname, realname, newName, function(resp) {
            window.location.reload();
        });
    });
};

// 打开选项对话框
FileView.openOptionDialog = function (target, event) {
    // console.log(event);
    event.preventDefault();
    event.stopPropagation();
    console.log(target);
    var filePath = $(target).attr("data-path");
    var fileName = $(target).attr("data-name");
    var fileRealName = $(target).attr("data-realname");
    var dialogId = xnote.dialog.createNewId();

    var html = $("#fileItemOptionDialog").render({
        "filePath": filePath,
        "fileName": fileName,
        "fileRealName": fileRealName,
        "dialogId": dialogId,
    });

    var options = {};
    options.title = "选项";
    options.html  = html;
    options.dialogId = dialogId;

    xnote.openDialogEx(options);
};

// 查看文件详情
FileView.showDetail = function(target) {
    var dataPath = $(target).attr("data-path");
    var params = {fpath: dataPath};
    xnote.http.get("/fs_api/detail", params, function(resp) {
        var message = ""
        if (resp.success) {
            message = resp.data;
        } else {
            message = resp.message;
        }
        xnote.showTextDialog("文件详情", message);
    })
};

// 移除收藏夹
FileView.removeBookmark = function(event) {
    event.preventDefault();
    var path = $(event.target).attr("data-path")
    var params = {
        action:"remove",
        path: path,
    }

    xnote.confirm("确定要取消收藏文件<code color=red>" + path + "</code>?", function () {        
        xnote.http.post("/fs_api/bookmark", params, function (resp) {
            if (resp.code == "success") {
                window.location.reload()
            } else {
                xnote.alert("取消收藏失败，请稍后重试!")
            }
        })
    })
}