
var NoteView = {};
xnote.action.note = NoteView;
xnote.note = NoteView;

NoteView.wangEditor = null; // wangEditor
NoteView.defaultParentId = 0; // 默认的父级节点
NoteView.groupId = 0; // 当前笔记本

var noteAPI = {};
xnote.api.note = noteAPI;


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

/**
 * 创建笔记接口
 * @param {object} req
 * @param {string} req.name 笔记名称
 * @param {string} req.parentId 上级目录id
 * @param {string} req.type 笔记类型
 * @param {callback} req.callback 回调函数
 */
NoteView.create = function (req) {
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

xnote.api["note.create"] = NoteView.create;

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

// 绑定标签
noteAPI.bindTag = function (cmd) {
    var currentTags = cmd.currentTags;
    var targetId = cmd.targetId;

    if (cmd.tagType != "group" && cmd.tagType != "note") {
        throw new TypeError("无效的tagType");
    }

    // 渲染绑定标签的html
    var html = cmd.html;
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
        tags_json: tagsJson
    };

    xnote.http.get("/note/tag/bind_dialog", listParams, function (html) {
        var cmd = {
            tagType: "note", // 绑定类型始终是note
            currentTags: JSON.parse(tagsJson),
            noteId: noteId,
            manageLink: "/note/manage?parent_id=" + parentId,
        };
        cmd.html = html;
        // 调用绑定标签组件
        noteAPI.bindTag(cmd);
    })
};

NoteView.searchNote = function () {
    var self = this;
    var searchText = $("#note-search-text").val();
    var api = "";
    if (searchText == "") {
        api = "/note/timeline/search_dialog?action=item_list&limit=100";
    } else {
        api = "/note/timeline/search_dialog?action=item_list&limit=100&key=" + searchText;
    }
    xnote.http.get(api, function (html) {
        $(".note-search-dialog-body").html(html);
    });
};

NoteView.openDialogToAddNote = function (event) {
    var tagCode = $(event.target).attr("data-code");
    xnote.http.get("/note/timeline/search_dialog?limit=100", function (html) {
        xnote.openDialog("选择笔记", html, ["确定", "取消"], function () {
            NoteView.addNoteToTag(tagCode);
        });
    });
};


/**
 * @param {options.callback} 回调函数 
 */
NoteView.openSearchNoteDialog = function (options) {
    var callback = options.callback;

    xnote.http.get("/note/timeline/search_dialog?limit=100", function (html) {
        var dialogOptions = {};
        dialogOptions.title = "选择笔记";
        dialogOptions.buttons = ["确认", "取消"];
        dialogOptions.closeForYes = false;
        dialogOptions.html = html;

        var yesFunction = function () {
            var noteList = [];
            $(".select-note-checkbox:checked").each(function (idx, ele) {
                var noteId = $(ele).attr("data-id");
                var noteName = $(ele).attr("data-name");
                var url = $(ele).attr("data-url");
                var noteInfo = {
                    "note_id": noteId,
                    "name": noteName,
                    "url": url
                }
                noteList.push(noteInfo);
            });
            console.log(noteList);
            // result: {close:bool}
            var result = callback(noteList);
            console.info("callback result:", result, dialogOptions.layerIndex);
            if (result) {
                if (result.close) {
                    layer.close(dialogOptions.layerIndex);
                }
            }
        }

        dialogOptions.functions = [yesFunction];
        xnote.openDialogEx(dialogOptions);
    });
}

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

/**
 * 选择笔记本-平铺视图
 * 这个函数需要配合 group_select_script.html 使用
 * @param {object} req 
 * @param {string} req.noteId 笔记ID
 * @param {callback} req.callback 回调函数,参数是 (selectedId: int)
 */
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
        var tagCodeList = [];
        $(".tag.delete.active").each(function (idx, ele) {
            var tagCode = $(ele).attr("data-tag-code");
            tagCodeList.push(tagCode);
        });

        var deleteParams = {
            tag_type: "group",
            group_id: NoteView.groupId,
            tag_code_list: JSON.stringify(tagCodeList),
        };
        xnote.http.post("/note/tag/delete", deleteParams, function (resp) {
            if (!resp.code) {
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
NoteView.openDialogToMove = function (noteIds) {
    if (noteIds == undefined) {
        xnote.alert("noteIds 不能为空");
        return;
    }
    var req = {};
    req.callback = function (parentId) {
        if (parentId === undefined || parentId == "") {
            xnote.alert("parentId is undefined");
            return;
        }
        xnote.http.post("/note/move", { note_ids: noteIds, parent_id: parentId }, function (resp) {
            if (resp.success) {
                console.log(resp);
                window.location.reload();
            } else {
                xnote.alert(resp.message);
            }
        });
    };
    this.selectGroupFlat(req);
};

NoteView.openDialogToBatchMove = function (selector) {
    var selected = $(selector);
    if (selected.length == 0) {
        xnote.alert("请先选中笔记本");
        return;
    }
    var noteIds = [];
    selected.each(function (index, elem) {
        noteIds.push($(elem).attr("data-id"));
    })
    xnote.note.openDialogToMove(noteIds.join(","));
}

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
    var params = { note_id: id };
    var ajax_dialog_url = "/note/ajax/share_group_dialog";
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

    xnote.http.post("/note/orderby", { id: id, orderby: orderby }, function (resp) {
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

    xnote.http.post("/note/status", { id: id, status: status }, function (resp) {
        var code = resp.code;
        if (code != "success") {
            xnote.alert(resp.message);
        } else {
            xnote.toast(resp.message);
            window.location.reload();
        }
    });
};

// 初始化wangEditor
NoteView.initWangEditor = function () {
    var editor = new wangEditor('#toolbar', "#editor");
    editor.customConfig.uploadImgServer = false;
    editor.customConfig.uploadImgShowBase64 = true;   // 使用 base64 保存图片
    editor.customConfig.linkImgCallback = function (link) {
        // 处理图片粘贴的回调
        // console.log(link);
    }
    editor.create();
    editor.txt.html($("#data").text());
    this.wangEditor = editor;
}

// 保存富文本文件
NoteView.savePost = function (target) {
    var noteId = $(target).attr("data-note-id");
    var version = $(target).attr("data-note-version");
    var data = this.wangEditor.txt.html();
    xnote.http.post("/note/save?type=html", { id: noteId, version: version, data: data }, function (resp) {
        console.log(resp);
        if (resp.success) {
            // window.location.reload();
            window.location.href = "/note/" + noteId;
        } else {
            xnote.alert(resp.message);
        }
    })
}

// 删除笔记
NoteView.remove = function (id, name, parentId, postAction) {
    var confirmed = xnote.confirm("确定删除'" + name + "'?", function (confirmed) {
        if (confirmed) {
            xnote.http.post("/note/remove", { id: id }, function (resp) {
                var code = resp.code;
                if (code != "success") {
                    xnote.alert(resp.message);
                } else {
                    if (postAction == "refresh") {
                        window.location.reload();
                    } else if (parentId) {
                        window.location.href = xnote.http.resolveURL("/note/" + parentId);
                    } else {
                        window.location.href = xnote.http.resolveURL("/");
                    }
                }
            })
        }
    });
}

// 删除笔记
NoteView.deleteByElement = function (target) {
    var noteId = $(target).attr("data-id");
    var name = $(target).attr("data-name");
    var parentId = $(target).attr("data-prent-id");
    var postAction = $(target).attr("data-post-action");
    NoteView.remove(noteId, name, parentId, postAction);
}

// 恢复笔记
NoteView.recover = function (noteId, callbackFn) {
    var params = {
        id: noteId
    };
    xnote.http.post("/note/recover", params, function (resp) {
        if (resp.code == "success") {
            callbackFn();
        } else {
            xnote.alert("恢复失败:" + resp.message);
        }
    }).fail(function (err) {
        xnote.alert("网络错误，请稍后重试");
    })
}


/** 创建分组
 * @param {string} parentId 父级笔记ID
 * @param {string} postAction 后置的动作 {refresh}  
 */
NoteView.createGroup = function (parentId, postAction) {
    var opName = "新建笔记本";

    if (parentId === undefined) {
        parentId = NoteView.defaultParentId;
    }

    xnote.prompt(opName, "", function (noteTitle) {
        var createOption = {};
        createOption.name = noteTitle;
        createOption.parent_id = parentId;
        createOption.type = "group";
        createOption._format = "json";
        xnote.http.post("/note/create", createOption, function (resp) {
            if (postAction == "refresh") {
                window.location.reload();
            } else if (resp.code == "success") {
                window.location = resp.url;
            } else {
                xnote.alert(opName + "失败:" + resp.message);
            }
        });
    });
}

// 别名
NoteView.createNotebook = NoteView.createGroup;

/**
 * 重命名笔记
 * @param {string} id 笔记ID
 * @param {string} oldName 旧的名称
 */
NoteView.rename = function (id, oldName) {
    xnote.prompt("新名称", oldName, function (newName) {
        console.log(newName);
        if (newName != "" && newName != null) {
            xnote.http.post("/note/rename", { id: id, name: newName }, function (resp) {
                var code = resp.code;
                if (code != "success") {
                    xnote.alert(resp.message);
                } else {
                    // $("#file-"+id).text(newName);
                    window.location.reload();
                }
            })
        }
    });
}

NoteView.renameByElement = function (target) {
    var id = $(target).attr("data-id");
    var oldName = $(target).attr("data-name");
    if (id == undefined || id == "") {
        xnote.alert("data-id为空");
        return;
    }

    if (oldName == undefined || oldName == "") {
        xnote.alert("data-name为空");
        return;
    }

    NoteView.rename(id, oldName);
}

NoteView.updateOrderType = function (target) {
    var noteId = $(target).attr("data-id");
    var orderType = $(target).attr("data-value");
    var params = {
        note_id: noteId,
        order_type: orderType
    }
    xnote.http.post("/note/order_type", params, function (resp) {
        if (resp.success) {
            window.location.reload();
        } else {
            xnote.alert(resp.message);
        }
    });
}

/**
 * 打开笔记预览
 * @param {Event} e 
 * @param {string} targetSelector 
 */
NoteView.openPreviewPopup = function (e, targetSelector) {
    e.preventDefault();
    var offset = $(e.target).offset();
    var name = $(e.target).text();
    console.log("name", name);
    if (xnote.isMobile()) {
        offset.left = 0;
    }
    xnote.http.get("/note/preview_popup?name="+encodeURIComponent(name), function (html) {
        if (html != "") {
            offset.top += 20;
            offset.left += 10;
            console.log("offset", offset);
            $(targetSelector).html(html).css(offset).show();
        }
    });
}