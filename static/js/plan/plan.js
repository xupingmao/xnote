var PlanView = {};
PlanView.state = {
    month: ""
};
xnote.action.plan = PlanView;

PlanView.addNote = function (target) {

    $.get("/note/api/timeline?type=all&limit=100",  function (resp) {
        if (resp.code != "success") {
            xnote.alert(resp.message);
        } else {
            var html = $("#select-note-tpl").render({
                itemList: resp.data
            });
            xnote.openDialog("选择笔记", html, ["加入计划", "取消"], function () {
                PlanView.addSelectedToPlan();
            });
        }
    });
};

PlanView.addSelectedToPlan = function () {
    var selectedIds = [];
    $(".select-note-checkbox:checked").each(function (idx, ele) {
        var dataId = $(ele).attr("data-id");
        selectedIds.push(dataId);
    });
    var params = {
        month: PlanView.state.month,
        note_ids: selectedIds.join(",")
    }
    $.post("/plan/month/add", params, function (resp) {
        if (resp.code == "success") {
            xnote.toast("加入成功");
            window.location.reload();
        } else {
            xnote.alert(resp.message);
        }
    }).fail(function (err) {
        xnote.alert("调用接口失败:" + err);
    })
};