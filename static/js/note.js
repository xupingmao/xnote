/**
 * 更新笔记的类目
 * @deprecated 已废弃
 * @param {object} req 更新请求
 */
xnote.updateNoteCategory = function (req) {
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

    xnote.http.post("/note/attribute/update", params, function (resp) {
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

        xnote.http.post("/api/note/category/update", params, function (resp) {
            if (resp.code == "success") {
                window.location.reload();
            } else {
                xnote.alert(resp.message);
            }
        });
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

    xnote.http.post("/note/create", createOption, function (resp) {
        if (resp.code == "success") {
            req.callback(resp);
        } else {
            xnote.alert(title + "失败:" + resp.message);
        }
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

    xnote.http.post("/note/copy", copyOption, function (resp) {
        if (resp.code == "success") {
            req.callback(resp);
        } else {
            xnote.alert(title + "失败:" + resp.message);
        }
    });
};

var noteAPI = {};
xnote.api.note = noteAPI;


// 绑定标签
noteAPI.bindTag = function (cmd) {
    var currentTags = cmd.currentTags;
    var tagList = cmd.tagList;
    var allTagList = cmd.allTagList; // 全部的标签
    var targetId = cmd.targetId;

    if (cmd.tagType != "group" && cmd.tagType != "note") {
        throw new TypeError("无效的tagType");
    }

    // 渲染绑定标签的html
    var html = $("#bindTagTemplate").render({
        tagList: tagList,
        allTagList: allTagList,
        selectedNames: currentTags,
        manageLink: cmd.manageLink,
        globalTagList: [
            { tag_name: "待办", tag_code: "$todo$" }
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

        xnote.http.post("/note/tag/bind", bindParams, function (resp) {
            if (resp.code != "success") {
                xnote.alert(resp.message);
            } else {
                xnote.toast("添加标签成功");
            }
            location.reload();
        });
    });
};


var NoteView = {};
xnote.action.note = NoteView;
xnote.note = NoteView;

NoteView.onTagClick = function (target) {
    $(target).toggleClass("active");
}

// 编辑笔记的标签
NoteView.editNoteTag = function (target) {
    var parentId = $(target).attr("data-parent-id");
    var noteId = $(target).attr("data-id");
    var tagsJson = $(target).attr("data-tags");
    var tagType = $(target).attr("data-tag-type");
    if (xnote.isEmpty(tagType)) {
        tagType = "note";
    }

    var listParams = {
        tag_type: tagType,
        group_id: parentId,
        v: 2,
    };

    xnote.http.get("/note/tag/list", listParams, function (resp) {
        var cmd = {
            tagType: "note", // 绑定类型始终是note
            currentTags: JSON.parse(tagsJson),
            noteId: noteId,
            manageLink: "/note/manage?parent_id=" + parentId,
        };
        // 推荐的标签
        cmd.tagList = resp.data.suggest_list;
        // 全部的标签
        cmd.allTagList = resp.data.all_list;
        // 调用绑定标签组件
        noteAPI.bindTag(cmd);
    })
};

NoteView.searchNote = function () {
    var self = this;
    var searchText = $("#note-search-text").val();
    var api = "";
    if (searchText == "") {
        api = "/note/api/timeline?type=all&limit=100";
    } else {
        api = "/note/api/timeline?type=search&key=" + searchText;
    }
    xnote.http.get(api, function (resp) {
        if (resp.code != "success") {
            xnote.toast(resp.message);
        } else {
            var templateText = self.getSelectNoteItemListTemplate();
            var html = template.render(templateText, {
                itemList: resp.data
            });
            $(".note-search-dialog-body").html(html);
        }
    });
};

NoteView.getSelectNoteItemListTemplate = function () {
    var text = "";
    text += "{{if itemList.length == 0 }}";
    text += "    <p class=\"align-center\">空空如也~</p>";
    text += "{{/if}}";
    text += "{{each itemList item}}";
    text += "<h3 class=\"card-title-2\">{{item.title}}</h3>";
    text += "    {{each item.children subItem }}";
    text += "    <p class=\"card-row share-dialog-row\">";
    text += "        <i class=\"fa {{subItem.icon}}\"></i>";
    text += "        <a href=\"{{subItem.url}}\">{{subItem.name}}</a>";
    text += "        <input type=\"checkbox\"";
    text += "            class=\"select-note-checkbox float-right\" ";
    text += "            data-id=\"{{subItem.id}}\">";
    text += "    <p>";
    text += "    {{/each}}";
    text += "{{/each}}";
    return text;
}

NoteView.getSelectNoteDialogTemplate = function () {
    var text = "";
    text += "<div class=\"card\">";
    text += "<div class=\"row\">";
    text += "    <input type=\"text\" class=\"nav-search-input\" id=\"note-search-text\" placeholder=\"搜索笔记\" ";
    text += "        value=\"{{searchText}}\" onkeyup=\"xnote.action.note.searchNote(this);\">";
    text += "    <button class=\"nav-search-btn btn-default\" onclick=\"xnote.action.note.searchNote(this)\">";
    text += "        <i class=\"fa fa-search\"></i>";
    text += "    </button>";
    text += "</div>";
    text += "<div class=\"row note-search-dialog-body\" style=\"padding-top: 10px;\">";
    text += this.getSelectNoteItemListTemplate();
    text += "</div>";
    text += "</div>";
    return text;
};


NoteView.renderNoteList = function (itemList) {
    var templateText = this.getSelectNoteDialogTemplate();
    var html = template.render(templateText, {
        itemList: itemList
    });
    return html;
};

NoteView.openDialogToAddNote = function (event) {
    var tagCode = $(event.target).attr("data-code");
    xnote.http.get("/note/api/timeline?type=all&limit=100", function (resp) {
        if (resp.code != "success") {
            xnote.alert(resp.message);
        } else {
            var html = NoteView.renderNoteList(resp.data);
            xnote.openDialog("选择笔记", html, ["确定", "取消"], function () {
                NoteView.addNoteToTag(tagCode);
            });
        }
    });
};

NoteView.addNoteToTag = function (tagCode) {
    var selectedIds = [];
    $(".select-note-checkbox:checked").each(function (idx, ele) {
        var noteId = $(ele).attr("data-id");
        selectedIds.push(noteId);
    });
    console.log(selectedIds);

    var params = {
        action: "add_note_to_tag",
        tag_code: tagCode,
        note_ids: selectedIds.join(",")
    };
    xnote.http.post("/note/tag/bind", params, function (resp) {
        if (resp.code != "success") {
            xnote.alert(resp.message);
        } else {
            xnote.toast("添加成功");
            location.reload();
        }
    });
};

// 选择笔记本-平铺视图
// 这个函数需要配合group_select_script.html使用
NoteView.selectGroupFlat = function (req) {
    var noteId = req.noteId;
    var respData;

    xnote.validate.isFunction(req.callback, "参数callback无效");

    function bindEvent() {
        $(".group-select-box").on("keyup", ".nav-search-input", function (event) {
            /* Act on the event */
            // console.log("event", event);
            var searchKey = $(this).val().toLowerCase();

            var newData = [];

            for (var i = 0; i < respData.length; i++) {
                var item = respData[i];
                if (item.name.toLowerCase().indexOf(searchKey) >= 0) {
                    newData.push(item);
                }
            }
            renderData(newData);
        });

        $(".group-select-box").on("click", ".link", function (event) {
            var dataId = $(event.target).attr("data-id");
            req.callback(dataId);
        });
    }

    function Section() {
        this.children = [];
        this.title = "title";
    }

    Section.prototype.add = function (item) {
        this.children.push(item);
    }

    Section.prototype.isVisible = function () {
        return this.children.length > 0;
    }

    // 渲染数据
    function renderData(data) {
        var first = new Section();
        var second = new Section();
        var last = new Section();
        var firstGroup = new Section(); // 一级笔记本
        for (var i = 0; i < data.length; i++) {
            var item = data[i];
            if (item.level >= 1) {
                first.add(item);
            } else if (item.level < 0) {
                last.add(item);
            } else if (item.parent_id == 0) {
                firstGroup.add(item);
            } else {
                second.add(item);
            }
        }

        first.title = "置顶";
        firstGroup.title = "一级笔记本";
        second.title = "其他笔记本";
        last.title = "归档";

        var groups = [first, firstGroup, second, last];
        var hasNoMatch = (data.length === 0);

        var html = $("#group_select_tpl").renderTemplate({
            groups: groups,
            noteId: noteId,
            hasNoMatch: hasNoMatch
        });
        $(".group-select-data").html(html);
    }

    xnote.http.get("/note/api/group?list_type=all&orderby=name", function (resp) {
        if (resp.code != "success") {
            xnote.alert(resp.message);
            return;
        }

        respData = resp.data;
        xnote.showDialog("移动笔记", $(".group-select-box"));
        // 绑定事件
        bindEvent();
        // 渲染数据
        renderData(respData);
    });
};

// 选择笔记本-树视图
NoteView.selectGroupTree = function () {
    // 树视图目前用的是html-ajax接口   
}

// 删除标签元信息
NoteView.deleteTagMeta = function (tagMetaList) {
    var html = $("#deleteTagTemplate").render({
        tagList: tagMetaList,
    });

    xnote.openDialog("删除标签", html, ["确定删除", "取消"], function () {
        var tagIds = [];
        $(".tag.delete.active").each(function (idx, ele) {
            var tagId = $(ele).attr("data-id");
            tagIds.push(tagId);
        });

        var deleteParams = {
            tag_type: "group",
            tag_ids: JSON.stringify(tagIds),
        };
        xnote.http.post("/note/tag/delete", deleteParams, function (resp) {
            if (resp.code != "success") {
                xnote.alert(resp.message);
            } else {
                xnote.toast("删除成功,准备刷新...");
                setTimeout(function () {
                    window.location.reload()
                }, 500);
            }
            refreshTagTop();
        });
    });
};

// 打开对话框移动笔记
NoteView.openDialogToMove = function (note_id) {
    var req = {};
    req.callback = function (parentId) {
        if (parentId === undefined || parentId == "") {
            xnote.alert("parentId is undefined");
            return;
        }
        xnote.http.post("/note/move", { id: note_id, parent_id: parentId }, function (resp) {
            console.log(resp);
            window.location.reload();
        });
    };
    this.selectGroupFlat(req);
};

// 打开对话框移动笔记
NoteView.openDialogToMoveByElement = function (target) {
    return this.openDialogToMove($(target).attr("data-id"));
}


// 点击标签操作
NoteView.onTagClick = function (target) {
    $(target).toggleClass("active");
}

// 打开对话框进行分享
NoteView.openDialogToShare = function (target) {
    var id = $(target).attr("data-id");
    var type = $(target).attr("data-note-type");
    var params = {note_id: id};
    var ajax_dialog_url   = "/note/ajax/share_group_dialog";
    var ajax_dialog_title = "分享笔记本";

    if (type != "group") {
        ajax_dialog_url = "/note/ajax/share_note_dialog";
        ajax_dialog_title = "分享笔记";
    }

    xnote.http.get(ajax_dialog_url, params, function (resp) {
        xnote.showDialog(ajax_dialog_title, resp);
    });
}

// 修改排序
NoteView.changeOrderBy = function (target) {
    var id = $(target).attr("data-id");
    var orderby = $(target).val();

    checkNotEmpty(id, "data-id为空");
    checkNotEmpty(orderby, "data-orderby为空");

    xnote.http.post("/note/orderby", {id: id, orderby: orderby}, function (resp) {
        var code = resp.code;
        if (code != "success") {
            xnote.alert(resp.message);
        } else {
            xnote.toast(resp.message);
            window.location.reload();
        }
    })
};

// 修改笔记的等级（置顶之类的）
NoteView.changeLevel = function (target) {
    var id = $(target).attr("data-id");
    var status = $(target).val();

    checkNotEmpty(id, "data-id为空");
    checkNotEmpty(status, "data-status为空");

    xnote.http.post("/note/status", {id: id, status: status}, function (resp) {
        var code = resp.code;
        if (code != "success") {
            xnote.alert(resp.message);
        } else {
            xnote.toast(resp.message);
            window.location.reload();
        }
    });
}