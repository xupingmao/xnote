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
    var dirname = $("#currentDir").val();
    xnote.prompt("输入新的文件名", oldName, function (newName) {
        FileAPI.rename(dirname, oldName, newName, function(resp) {
            window.location.reload();
        });
    });
};
