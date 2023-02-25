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

var noteAPI = {};
xnote.api.note = noteAPI;


// 绑定标签
noteAPI.bindTag = function (cmd) {
    var currentTags = cmd.currentTags;
    var tagList = cmd.tagList;
    var targetId = cmd.targetId;
    
    if (cmd.tagType != "group" && cmd.tagType != "note") {
        throw new TypeError("无效的tagType");
    }

    // 渲染绑定标签的html
    var html = $("#bindTagTemplate").render({
        tagList: tagList,
        selectedNames: currentTags,
        manageLink: cmd.manageLink,
        globalTagList: [
            {tag_name: "待办", tag_code: "$todo$"}
        ],
    });

    console.log("bind-tag-dialog", html);

    xnote.openDialog("添加标签", html, ["确定", "取消"], function () {
        var selectedNames = [];
        $(".tag.bind.active").each(function (idx, ele) {
            var tagName = $(ele).attr("data-code");
            selectedNames.push(tagName);
        });

        var bindParams = {
            tag_type: cmd.tagType,
            group_id: cmd.groupId,
            note_id: cmd.noteId,
            tag_names: JSON.stringify(selectedNames),
        };

        $.post("/note/tag/bind", bindParams, function (resp) {
            if (resp.code != "success") {
                xnote.alert(resp.message);
            } else {
                xnote.toast("添加标签成功");
            }
            location.reload();
        }).fail(function (err) {
            console.error(err);
            xnote.alert("系统繁忙，请稍后重试");
        })
    });
}


var NoteView = {};
xnote.action.note = NoteView;

// 编辑笔记的标签
NoteView.editNoteTag = function (target) {
    var parentId = $(target).attr("data-parent-id");
    var noteId = $(target).attr("data-id");

    var listParams = {
        tag_type:"note",
        group_id:parentId,
    };

    $.get("/note/tag/list", listParams, function (resp) {
        var tagsJson = $("#noteTagJson").val();
        var cmd = {
            tagType: "note",
            currentTags: JSON.parse(tagsJson),
            noteId: noteId,
            manageLink: "/note/manage?parent_id=" + parentId,
        };
        cmd.tagList = resp.data;
        // 调用绑定标签组件
        xnote.api.note.bindTag(cmd);
    })
};


NoteView.renderNoteList = function (itemList) {
    var html = $("#select-note-tpl").render({
        itemList: itemList
    });
    $("#select-note-dialog-body").html(html);
};


NoteView.openDialogToAddNote = function (event) {
    $.get("/note/api/timeline?type=all&limit=100",  function (resp) {
        if (resp.code != "success") {
            xnote.alert(resp.message);
        } else {
            var html = NoteView.renderNoteList(resp.data);
            var dialogEle = $("#select-note-dialog").html(html);
            xnote.openDialog("选择笔记", dialogEle, ["确定", "取消"], function () {
                NoteView.addNoteToTag();
            });
        }
    });
};