/**
 * 更新笔记的类目
 * @param {object} req 更新请求
 */
xnote.updateNoteCategory = function(req) {
    if (req === undefined) {
        throw new Error("req is undefined");
    }
    if (req.noteId === undefined) {
        throw new Error("req.noteId is undefined");
    }
    if (req.value === undefined) {
        throw new Error("req.value is undefined");
    }

    var params = {
        id: req.noteId,
        key: "category",
        value: req.value
    };
    
    $.post("/note/attribute/update", params, function (resp) {
        console.log("update category", resp);
        if (resp.code == "success") {
            xnote.toast("更新类目成功");
            if (req.doRefresh) {
                window.location.reload();
            }
        } else {
            xnote.alert(resp.message);
        }
    });
};

/**
 * 更新类目的名称
 * @param {object} req 请求对象
 */
xnote.updateCategoryName = function (req) {
    if (req === undefined) {
        throw new Error("req is undefined");
    }
    if (req.oldName === undefined) {
        throw new Error("req.oldName is undefined");
    }
    if (req.code === undefined) {
        throw new Error("req.code is undefined");
    }

    xnote.prompt("重命名类目", req.oldName, function (newName) {
        var params = {
            code: req.code,
            name: newName
        };

        $.post("/api/note/category/update", params, function(resp) {
            if (resp.code=="success") {
                window.location.reload();
            } else {
                xnote.alert(resp.message);
            }
        })
    });
};

// 创建笔记接口
xnote.api["note.create"] = function (req) {
    xnote.validate.notUndefined(req.name, "req.name is undefined");
    xnote.validate.notUndefined(req.parentId, "req.parentId is undefined");
    xnote.validate.notUndefined(req.type, "req.type is undefined");
    xnote.validate.isFunction(req.callback, "req.callback is not function");

    var createOption = {};
    createOption.name = req.name;
    createOption.parent_id = req.parentId;
    createOption.type = req.type;
    createOption._format = "json";

    var title = req.name;
    
    $.post("/note/create", createOption, function (resp) {
        if (resp.code == "success") {
            req.callback(resp);
        } else {
            xnote.alert(title + "失败:" + resp.message);
        }
    }).fail(function (e) {
        console.error(title + "失败", e);
        xnote.alert(title + "失败:" + e);
    });
};

// 复制笔记接口
xnote.api["note.copy"] = function (req) {
    xnote.validate.notUndefined(req.name, "req.name is undefined");
    xnote.validate.notUndefined(req.originId, "req.originId is undefined");
    var copyOption = {
        name: req.name,
        origin_id: req.originId
    };
    var title = req.name;

    $.post("/note/copy", copyOption, function (resp) {
        if (resp.code == "success") {
            req.callback(resp);
        } else {
            xnote.alert(title + "失败:" + resp.message);
        }
    }).fail(function (e) {
        console.error("Copy " + title + "失败", e);
        xnote.alert("Copy " + title + "失败:" + e);
    });
};
