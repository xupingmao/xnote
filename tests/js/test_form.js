/**
 * 单元测试: _static/js/xnote-ui/x-form.js 中 oninput_ajax_url 的逻辑
 *
 * 该文件依赖浏览器环境（jQuery / DOM），这里用最小的 jQuery 桩 + 假元素在 vm 沙箱中加载，
 * 然后验证「值变化 -> 防抖 -> 发 ajax -> 执行返回的命令」的行为。
 *
 * 运行: node tests/js/test_form.js
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");

const SRC = path.join(__dirname, "..", "..", "_static", "js", "xnote-ui", "x-form.js");

let passed = 0;
let failed = 0;

function check(name, fn) {
    return Promise.resolve()
        .then(fn)
        .then(() => {
            passed++;
            console.log("  PASS: " + name);
        })
        .catch((err) => {
            failed++;
            console.log("  FAIL: " + name + " -> " + err.message);
        });
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

/** 判断假元素是否匹配选择器（只实现 x-form.js 用到的那几个） */
function match(elem, selector) {
    if (selector === ".x-form") {
        return elem.isForm === true;
    }
    if (selector === "textarea") {
        return elem.tag === "textarea";
    }
    if (selector === ".form-date") {
        return (elem.classes || []).indexOf("form-date") >= 0;
    }
    if (selector === ".form-upload-row") {
        return (elem.classes || []).indexOf("form-upload-row") >= 0;
    }
    if (selector === "[data-oninput-ajax-url]") {
        return elem.attrs["data-oninput-ajax-url"] !== undefined;
    }
    return false;
}

function wrap(list) {
    const wrapper = {
        length: list.length,
        each: function (fn) {
            for (let i = 0; i < list.length; i++) {
                fn.call(list[i], i, list[i]);
            }
            return wrapper;
        },
        attr: function (name, value) {
            if (value === undefined) {
                return list.length ? list[0].attrs[name] : undefined;
            }
            for (const item of list) {
                item.attrs[name] = value;
            }
            return wrapper;
        },
        val: function () {
            return list.length ? list[0].value : undefined;
        },
        is: function (selector) {
            return list.length > 0 && list[0].tag === selector;
        },
        on: function (event, fn) {
            for (const item of list) {
                if (!item.events[event]) {
                    item.events[event] = [];
                }
                item.events[event].push(fn);
            }
            return wrapper;
        },
        find: function (selector) {
            const result = [];
            for (const item of list) {
                for (const child of item.children || []) {
                    if (match(child, selector)) {
                        result.push(child);
                    }
                }
            }
            return wrap(result);
        },
        /** 模拟输入: 触发绑定的事件 */
        trigger: function (event) {
            for (const item of list) {
                for (const fn of item.events[event] || []) {
                    fn.call(item);
                }
            }
            return wrapper;
        },
    };
    return wrapper;
}

/** 假 input/select 元素 */
function createInput(tag, name, value, attrs) {
    return {
        tag: tag || "input",
        classes: [],
        attrs: Object.assign({ name: name }, attrs || {}),
        value: value || "",
        events: {},
    };
}

/** 假表单 */
function createForm(children) {
    return { isForm: true, classes: [], attrs: {}, events: {}, children: children || [] };
}

/**
 * 加载 x-form.js，http.post 的每次调用记录在 sandbox.calls 里
 */
function createSandbox(response) {
    const calls = [];
    const executed = [];
    const toasts = [];

    const xnote = {
        config: { serverHome: "" },
        layout: {},
        http: {
            post: function (url, params, callback) {
                calls.push({ url: url, params: params });
                callback(response);
            },
        },
        executeCommands: function (commands) {
            executed.push(commands);
        },
        toast: function (message) {
            toasts.push(message);
        },
        alert: function (message) {
            toasts.push(message);
        },
    };

    const $ = function (arg) {
        if (typeof arg === "function") {
            return; // $(function(){}) 的 ready 回调，测试里不执行
        }
        return wrap([arg]);
    };

    const sandbox = {
        $: $,
        xnote: xnote,
        console: console,
        setTimeout: setTimeout,
        clearTimeout: clearTimeout,
    };
    vm.runInNewContext(fs.readFileSync(SRC, "utf8"), sandbox, { filename: SRC });

    // 防抖时间设为0，避免测试等待
    sandbox.xnote.form.onInputDelay = 0;

    return { sandbox: sandbox, calls: calls, executed: executed, toasts: toasts };
}

const OK_RESPONSE = { success: true, data: [{ command: "update_value", name: "result", value: "v1" }] };

async function main() {
    await check("input 值变化 -> 发 ajax（带 name/value）并执行返回的命令", async () => {
        const env = createSandbox(OK_RESPONSE);
        const input = createInput("input", "keyword", "abc", { "data-oninput-ajax-url": "/api/on_input" });
        const form = createForm([input]);

        env.sandbox.xnote.form.initOnInputAjax(wrap([form]));
        input.value = "abcd";
        wrap([input]).trigger("input");
        await sleep(20);

        assert.strictEqual(env.calls.length, 1);
        assert.strictEqual(env.calls[0].url, "/api/on_input");
        assert.strictEqual(env.calls[0].params.name, "keyword");
        assert.strictEqual(env.calls[0].params.value, "abcd");
        assert.deepStrictEqual(env.executed, [OK_RESPONSE.data]);
    });

    await check("连续输入只发一次请求（防抖）", async () => {
        const env = createSandbox(OK_RESPONSE);
        const input = createInput("input", "keyword", "", { "data-oninput-ajax-url": "/api/on_input" });
        const form = createForm([input]);

        env.sandbox.xnote.form.initOnInputAjax(wrap([form]));
        wrap([input]).trigger("input");
        wrap([input]).trigger("input");
        wrap([input]).trigger("input");
        await sleep(20);

        assert.strictEqual(env.calls.length, 1);
    });

    await check("没有 data-oninput-ajax-url 的 input 不绑定", async () => {
        const env = createSandbox(OK_RESPONSE);
        const input = createInput("input", "keyword", "");
        const form = createForm([input]);

        env.sandbox.xnote.form.initOnInputAjax(wrap([form]));
        env.sandbox.xnote.form.initOnInputAjax(wrap([form]));
        await sleep(20);

        assert.strictEqual(input.events.input, undefined);
        assert.strictEqual(env.calls.length, 0);
    });

    await check("重复初始化不会重复绑定（只发一次请求）", async () => {
        const env = createSandbox(OK_RESPONSE);
        const input = createInput("input", "keyword", "", { "data-oninput-ajax-url": "/api/on_input" });
        const form = createForm([input]);

        env.sandbox.xnote.form.initOnInputAjax(wrap([form]));
        env.sandbox.xnote.form.initOnInputAjax(wrap([form]));
        wrap([input]).trigger("input");
        await sleep(20);

        assert.strictEqual(env.calls.length, 1);
    });

    await check("select 用 change 事件（而不是 input）", async () => {
        const env = createSandbox(OK_RESPONSE);
        const select = createInput("select", "type", "1", { "data-oninput-ajax-url": "/api/on_input" });
        const form = createForm([select]);

        env.sandbox.xnote.form.initOnInputAjax(wrap([form]));

        assert.strictEqual((select.events.input || []).length, 0);
        assert.strictEqual((select.events.change || []).length, 1);

        wrap([select]).trigger("change");
        await sleep(20);
        assert.strictEqual(env.calls.length, 1);
    });

    await check("请求失败: 提示 message，不执行命令", async () => {
        const env = createSandbox({ success: false, message: "出错了" });
        const input = createInput("input", "keyword", "", { "data-oninput-ajax-url": "/api/on_input" });
        const form = createForm([input]);

        env.sandbox.xnote.form.initOnInputAjax(wrap([form]));
        wrap([input]).trigger("input");
        await sleep(20);

        assert.deepStrictEqual(env.toasts, ["出错了"]);
        assert.strictEqual(env.executed.length, 0);
    });

    await check("initForm: 只初始化 .x-form 里的表单，且只初始化一次", async () => {
        const env = createSandbox(OK_RESPONSE);
        const input = createInput("input", "keyword", "", { "data-oninput-ajax-url": "/api/on_input" });
        const form = createForm([input]);
        const root = { isForm: false, classes: [], attrs: {}, events: {}, children: [form] };

        env.sandbox.xnote.initForm(root);
        env.sandbox.xnote.initForm(root);

        assert.strictEqual(form.attrs["data-form-bind"], "1");
        assert.strictEqual((input.events.input || []).length, 1);

        wrap([input]).trigger("input");
        await sleep(20);
        assert.strictEqual(env.calls.length, 1);
    });

    console.log("\n结果: " + passed + " passed, " + failed + " failed");
    process.exit(failed === 0 ? 0 : 1);
}

main();
