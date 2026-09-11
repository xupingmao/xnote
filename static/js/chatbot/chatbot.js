// 聊天机器人页面逻辑(桌面端 + 移动端共用)
// 注意: 本项目 static/js 下的运行时代码需要兼容 ES3 语法

(function () {

    var API_SEND = "/api/chatbot/send";
    var API_SESSION_DELETE = "/api/chatbot/session/delete";

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

        // 移动端标题同步为会话标题
        if (data.session && data.session.title) {
            $("#chat-mobile-title").text(data.session.title);
        }
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

    function deleteSession(btn) {
        var sessionId = parseInt($(btn).attr("data-session-id"), 10);
        if (isNaN(sessionId)) {
            return;
        }

        xnote.confirm("确定删除该会话?", function (ok) {
            if (!ok) {
                return;
            }

            xnote.http.post(API_SESSION_DELETE, { session_id: sessionId }, function (resp) {
                if (!resp.success) {
                    xnote.toast(resp.message);
                    return;
                }
                var item = $(btn).closest(".chat-session-item");
                var wasActive = item.hasClass("active");
                item.remove();
                // 删除的是当前会话, 回到"新建会话"空状态
                if (wasActive) {
                    window.location.href = "?action=new";
                }
            }, "json");
        });
    }

    function toggleSessionDrawer() {
        $("#chat-session-drawer").toggleClass("open");
        $("#chat-session-mask").toggleClass("open");
    }

    function bindEvents() {
        $("#chat-send-btn").click(function () {
            sendMessage();
        });

        $("#chat-input").keydown(function (event) {
            if (event.keyCode === 13) {
                if (event.ctrlKey) {
                    // Ctrl+Enter 换行, 不拦截
                    return;
                }
                // Enter 发送, 阻止默认的换行
                event.preventDefault();
                sendMessage();
            }
        });

        // 删除会话(事件委托, 兼容后端刷新后的新节点)
        $("#session-list-inner").on("click", ".chat-session-delete", function () {
            deleteSession(this);
        });

        // 移动端会话抽屉(桌面端无这些元素, 绑定为空操作)
        $("#chat-session-toggle").click(toggleSessionDrawer);
        $("#chat-session-mask").click(toggleSessionDrawer);
    }

    function init() {
        bindEvents();
        scrollToBottom();
    }

    $(function () {
        init();
    });

})();