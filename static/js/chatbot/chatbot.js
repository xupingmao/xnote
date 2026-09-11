// 聊天机器人页面逻辑
// 注意: 本项目 static/js 下的运行时代码需要兼容 ES3 语法

(function () {

    var API_SEND = "/api/chatbot/send";

    var sending = false;

    function getSessionId() {
        var value = parseInt($("#current-session-id").val(), 10);
        if (isNaN(value)) {
            return 0;
        }
        return value;
    }

    function scrollToBottom() {
        var list = $("#message-list");
        list.scrollTop(list[0].scrollHeight);
    }

    // 后端渲染好 HTML 片段并下发命令, 由 xnote.executeCommands 执行
    function onSendSuccess(resp) {
        if (!resp.success) {
            xnote.toast(resp.message);
            return;
        }

        var data = resp.data;
        if (data.commands && data.commands.length) {
            xnote.executeCommands(data.commands);
        }
        // 命令通过 setTimeout 异步执行, 等 DOM 更新后再滚到底部
        setTimeout(scrollToBottom, 0);
    }

    function sendMessage() {
        var input = $("#chat-input");
        var content = $.trim(input.val());

        if (content === "") {
            return;
        }
        if (sending) {
            return;
        }

        sending = true;
        var params = { session_id: getSessionId(), content: content };
        input.val("");

        xnote.http.post(API_SEND, params, function (resp) {
            onSendSuccess(resp);
        }, "json").always(function () {
            sending = false;
        });
    }

    function bindEvents() {
        $("#chat-send-btn").click(function () {
            sendMessage();
        });

        $("#chat-input").keydown(function (event) {
            // Ctrl+Enter 发送
            if (event.ctrlKey && event.keyCode === 13) {
                sendMessage();
            }
        });
    }

    function init() {
        bindEvents();
        scrollToBottom();
    }

    $(function () {
        init();
    });

})();