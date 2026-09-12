var PlanView = {};
PlanView.state = {
    month: "",
    id: ""
};
xnote.action.plan = PlanView;

PlanView.addNote = function (target) {
    xnote.http.get("/note/timeline/search_dialog?limit=100", function (html) {
        xnote.openDialog("选择笔记", html, ["加入计划", "取消"], function () {
            PlanView.addSelectedToPlan();
        });
    });
};


PlanView.removeNote = function (target) {
    window.event.preventDefault();
    window.event.stopPropagation();
    
    var noteId = $(target).attr("data-id");
    var noteName = $(target).attr("data-name");
    var params = {
        id: PlanView.state.id,
        note_id: noteId
    };

    xnote.confirm("确认要取消关注[" + noteName + "]吗?", function () {
        xnote.http.post("/plan/month/remove", params, function (resp) {
            if (resp.success) {
                xnote.toast("取消关注成功");
                window.location.reload();
            } else {
                xnote.alert(resp.message);
            }
        });
    });
};


PlanView.addSelectedToPlan = function () {
    var selectedIds = [];
    $(".select-note-checkbox:checked").each(function (idx, ele) {
        var dataId = $(ele).attr("data-id");
        selectedIds.push(dataId);
    });
    var params = {
        plan_id: PlanView.state.id,
        note_ids: selectedIds.join(",")
    }
    xnote.http.post("/plan/month/add", params, function (resp) {
        if (resp.code == "success") {
            xnote.toast("加入成功");
            window.location.reload();
        } else {
            xnote.alert(resp.message);
        }
    });
};
