// 聊天机器人页面逻辑(桌面端 + 移动端共用)
// 注意: 本项目 static/js 下的运行时代码需要兼容 ES3 语法

(function () {

    var API_SEND = "/api/chatbot/send";
    var API_SESSION_DELETE = "/api/chatbot/session/delete";
    var API_SESSION_RENAME = "/api/chatbot/session/rename";
    var API_SESSION_TOP = "/api/chatbot/session/top";

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

    function deleteSession(btn) {
        var sessionId = parseInt($(btn).attr("data-session-id"), 10);
        if (isNaN(sessionId)) {
            return;
        }

        xnote.confirm("确定删除该会话?", function (ok) {
            if (!ok) {
                return;
            }

            xnote.http.post(API_SESSION_DELETE,
                { session_id: sessionId, current_session_id: getSessionId() },
                function (resp) {
                    if (!resp.success) {
                        xnote.toast(resp.message);
                        return;
                    }
                    // 后端已把"刷新会话列表/重置空状态"封装成命令, 直接执行
                    if (resp.data && resp.data.commands) {
                        xnote.executeCommands(resp.data.commands);
                    }
                }, "json");
        });
    }

    function toggleSessionDrawer() {
        $("#chat-session-drawer").toggleClass("open");
        $("#chat-session-mask").toggleClass("open");
    }

    function renameSession(btn) {
        var item = $(btn).closest(".chat-session-item");
        var sessionId = parseInt($(btn).attr("data-session-id"), 10);
        if (isNaN(sessionId)) {
            return;
        }
        var oldTitle = item.attr("data-title") || "";

        xnote.prompt("重命名会话", oldTitle, function (newName) {
            if (newName == null) {
                return;
            }
            newName = $.trim(newName);
            if (newName === "") {
                xnote.toast("标题不能为空");
                return;
            }

            xnote.http.post(API_SESSION_RENAME,
                { session_id: sessionId, title: newName,
                  current_session_id: getSessionId() },
                function (resp) {
                    if (!resp.success) {
                        xnote.toast(resp.message);
                        return;
                    }
                    // 后端已把"刷新会话列表/同步标题"封装成命令, 直接执行
                    if (resp.data && resp.data.commands) {
                        xnote.executeCommands(resp.data.commands);
                    }
                }, "json");
        });
    }

    function pinSession(btn) {
        var sessionId = parseInt($(btn).attr("data-session-id"), 10);
        if (isNaN(sessionId)) {
            return;
        }

        xnote.http.post(API_SESSION_TOP,
            { session_id: sessionId, current_session_id: getSessionId() },
            function (resp) {
            if (!resp.success) {
                xnote.toast(resp.message);
                return;
            }
            // 后端刷新会话列表, 置顶项自动排到最前
            if (resp.data && resp.data.commands) {
                xnote.executeCommands(resp.data.commands);
            }
        }, "json");
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

        // 重命名会话(事件委托)
        $("#session-list-inner").on("click", ".chat-session-rename", function () {
            renameSession(this);
        });

        // 置顶/取消置顶(事件委托)
        $("#session-list-inner").on("click", ".chat-session-top", function () {
            pinSession(this);
        });

        // 移动端会话抽屉(桌面端无这些元素, 绑定为空操作)
        $("#chat-session-toggle").click(toggleSessionDrawer);
        $("#chat-session-mask").click(toggleSessionDrawer);

        // "更多"菜单: 点击 ⋮ 展开/收起
        // 展开前先收起其它已展开的菜单, 保证同时只有一个菜单打开;
        // stopPropagation 避免冒泡到 document 的外部关闭逻辑把刚展开的菜单又关掉
        $("#session-list-inner").on("click", ".x-more-menu-toggle", function (event) {
            event.stopPropagation();
            var menu = $(this).closest(".x-more-menu");
            $(".x-more-menu.open").not(menu).removeClass("open");
            menu.toggleClass("open");
        });

        // 点击菜单项后立即收起菜单(具体操作由下方的委托处理)
        $("#session-list-inner").on("click", ".x-more-menu-item", function () {
            $(this).closest(".x-more-menu").removeClass("open");
        });

        // 点击菜单外部时收起所有已展开的菜单
        $(document).on("click", function (event) {
            if (!$(event.target).closest(".x-more-menu").length) {
                $(".x-more-menu.open").removeClass("open");
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