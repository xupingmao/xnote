/**
 * 单元测试: _static/js/xnote-ui/x-tag-select.js 中 tag 风格选择器的交互逻辑
 *
 * 该文件依赖浏览器环境（jQuery / DOM），这里用最小的 jQuery 桩 + 假元素在 vm 沙箱中加载，
 * 然后验证「点击标签 -> 切换选中态 -> 同步隐藏域」的行为。
 *
 * 运行: node tests/js/test_tag_select.js
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");

const SRC = path.join(__dirname, "..", "..", "_static", "js", "xnote-ui", "x-tag-select.js");

let passed = 0;
let failed = 0;

function check(name, fn) {
    try {
        fn();
        passed++;
        console.log("  PASS: " + name);
    } catch (err) {
        failed++;
        console.log("  FAIL: " + name + " -> " + err.message);
    }
}

/** 假 tag 元素 */
function createTag(value, active) {
    return { classes: active ? ["tag", "lightblue", "active"] : ["tag", "lightblue"], attrs: { "data-value": value } };
}

/**
 * 构造一个 .form-tag-select 容器 + 隐藏域的假元素树，
 * 并实现 x-tag-select.js 用到的那部分 jQuery API。
 */
function createTagBox(multiple, value, tagCount) {
    const tags = [];
    for (let i = 1; i <= tagCount; i++) {
        const v = String(i);
        const tag = createTag(v, (value || "").split(",").indexOf(v) >= 0);
        tag.parentBox = null; // 由下面的 box 引用回填
        tags.push(tag);
    }

    const hidden = { attrs: { type: "hidden", name: "tags" }, value: value || "" };
    const box = {
        isBox: true,
        multiple: multiple,
        tags: tags,
        hidden: hidden,
        attrs: { "data-multiple": multiple ? "true" : "false" },
        events: {},
    };
    for (const tag of tags) {
        tag.parentBox = box;
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
            attr: function (name, val) {
                if (val === undefined) {
                    return list.length ? list[0].attrs[name] : undefined;
                }
                for (const item of list) {
                    item.attrs[name] = val;
                }
                return wrapper;
            },
            addClass: function (cls) {
                for (const item of list) {
                    if (item.classes.indexOf(cls) < 0) item.classes.push(cls);
                }
                return wrapper;
            },
            removeClass: function (cls) {
                for (const item of list) {
                    item.classes = item.classes.filter((c) => c !== cls);
                }
                return wrapper;
            },
            hasClass: function (cls) {
                return list.length > 0 && list[0].classes.indexOf(cls) >= 0;
            },
            toggleClass: function (cls) {
                for (const item of list) {
                    if (item.classes.indexOf(cls) >= 0) {
                        item.classes = item.classes.filter((c) => c !== cls);
                    } else {
                        item.classes.push(cls);
                    }
                }
                return wrapper;
            },
            not: function (other) {
                return wrap(list.filter((item) => !other.has(item)));
            },
            has: function (item) {
                return list.indexOf(item) >= 0;
            },
            val: function (val) {
                if (val === undefined) {
                    return list.length ? list[0].value : undefined;
                }
                for (const item of list) {
                    item.value = val;
                }
                return wrapper;
            },
            on: function (event, fn) {
                for (const item of list) {
                    if (!item.events[event]) item.events[event] = [];
                    item.events[event].push(fn);
                }
                return wrapper;
            },
            /** 事件委托: 记录 selector + handler，并模拟冒泡到匹配元素 */
            delegate: function (selector, event, fn) {
                for (const item of list) {
                    if (!item.events.delegated) item.events.delegated = [];
                    item.events.delegated.push({ selector: selector, event: event, fn: fn });
                }
                return wrapper;
            },
            /** 模拟点击: 只在 tag 命中委托 selector 时触发 */
            triggerDelegated: function (target) {
                for (const item of list) {
                    const entries = item.events.delegated || [];
                    for (const entry of entries) {
                        const matches = target && target.attrs && target.attrs["data-value"] !== undefined;
                        if (matches) {
                            entry.fn.call(item, { currentTarget: target, target: target });
                        }
                    }
                }
                return wrapper;
            },
            click: function (target) {
                for (const item of list) {
                    const handlers = item.events.click || [];
                    for (const fn of handlers) {
                        fn.call(item, { target: target });
                    }
                }
                return wrapper;
            },
            find: function (selector) {
                if (selector === ".form-tag-select") {
                    return wrap(list.filter((item) => item.isBox));
                }
                if (selector === ".tag.active") {
                    return wrap(list.flatMap((item) => item.tags.filter((t) => t.classes.indexOf("active") >= 0)));
                }
                if (selector === ".tag[data-value]") {
                    return wrap(list.flatMap((item) => item.tags));
                }
                if (selector === "input[type=hidden]") {
                    return wrap(list.map((item) => item.hidden));
                }
                throw new Error("unsupported selector: " + selector);
            },
            closest: function (selector) {
                if (selector === ".tag[data-value]") {
                    return wrap(list.filter((item) => item.attrs && item.attrs["data-value"] !== undefined));
                }
                if (selector === ".form-tag-select") {
                    const boxes = [];
                    for (const item of list) {
                        const b = item.isBox ? item : item.parentBox;
                        if (b && boxes.indexOf(b) < 0) boxes.push(b);
                    }
                    return wrap(boxes);
                }
                return wrap([]);
            },
        };
        return wrapper;
    }

    // 容器选择器: 返回 [box] 或其内部元素
    function $(arg) {
        if (typeof arg === "string") {
            if (arg === ".tag[data-value]") {
                return wrap(tags);
            }
            if (arg === ".form-tag-select") {
                return wrap([box]);
            }
            throw new Error("unsupported selector: " + arg);
        }
        if (arg && arg.classes) {
            return wrap([arg]); // 单个 tag
        }
        return wrap([arg]);
    }

    return { box: box, $: $, wrap: wrap };
}

function createSandbox($) {
    const sandbox = { $: $, xnote: {}, console: console };
    vm.runInNewContext(fs.readFileSync(SRC, "utf8"), sandbox, { filename: SRC });
    return sandbox;
}

check("initTagSelect: 以隐藏域的值初始化选中态", () => {
    const fixture = createTagBox(true, "1", 3);
    const sandbox = createSandbox(fixture.$);
    sandbox.xnote.initTagSelect(fixture.box);

    assert.strictEqual(fixture.box.tags[0].classes.indexOf("active") >= 0, true);
    assert.strictEqual(fixture.box.tags[1].classes.indexOf("active") >= 0, false);
});

check("多选: 点击未选中的标签 -> 选中并同步隐藏域", () => {
    const fixture = createTagBox(true, "1", 3);
    const sandbox = createSandbox(fixture.$);
    sandbox.xnote.initTagSelect(fixture.box);

    // 点击第 2 个标签
    sandbox.xnote.handleTagSelectClick(fixture.box.tags[1]);

    assert.strictEqual(fixture.box.tags[1].classes.indexOf("active") >= 0, true);
    assert.strictEqual(fixture.box.hidden.value, "1,2");
});

check("多选: 再次点击已选中的标签 -> 取消选中并同步隐藏域", () => {
    const fixture = createTagBox(true, "1,2", 3);
    const sandbox = createSandbox(fixture.$);
    sandbox.xnote.initTagSelect(fixture.box);

    sandbox.xnote.handleTagSelectClick(fixture.box.tags[1]);

    assert.strictEqual(fixture.box.tags[1].classes.indexOf("active") >= 0, false);
    assert.strictEqual(fixture.box.hidden.value, "1");
});

check("单选: 点击第二个标签 -> 取消第一个的选中态，隐藏域只保留新值", () => {
    const fixture = createTagBox(false, "1", 3);
    const sandbox = createSandbox(fixture.$);
    sandbox.xnote.initTagSelect(fixture.box);

    sandbox.xnote.handleTagSelectClick(fixture.box.tags[1]);

    assert.strictEqual(fixture.box.tags[0].classes.indexOf("active") >= 0, false);
    assert.strictEqual(fixture.box.tags[1].classes.indexOf("active") >= 0, true);
    assert.strictEqual(fixture.box.hidden.value, "2");
});

check("单选: 再次点击已选中的标签 -> 取消选中，隐藏域清空", () => {
    const fixture = createTagBox(false, "1", 3);
    const sandbox = createSandbox(fixture.$);
    sandbox.xnote.initTagSelect(fixture.box);

    sandbox.xnote.handleTagSelectClick(fixture.box.tags[0]);

    assert.strictEqual(fixture.box.tags[0].classes.indexOf("active") >= 0, false);
    assert.strictEqual(fixture.box.hidden.value, "");
});

check("重复初始化: 不会重复绑定事件", () => {
    const fixture = createTagBox(true, "1", 3);
    const sandbox = createSandbox(fixture.$);
    sandbox.xnote.initTagSelect(fixture.box);
    sandbox.xnote.initTagSelect(fixture.box);

    assert.strictEqual(fixture.box.events.delegated.length, 1);
});

check("事件委托: 绑定在 .tag 上（点到容器空白处不触发）", () => {
    const fixture = createTagBox(true, "1", 3);
    const sandbox = createSandbox(fixture.$);
    sandbox.xnote.initTagSelect(fixture.box);

    // 监听器挂在 .tag 上，而不是容器或 document
    assert.strictEqual(fixture.box.events.delegated[0].selector, ".tag[data-value]");
    assert.strictEqual(fixture.box.events.click, undefined);

    // 点到容器空白处（target 不匹配 .tag）→ 值不变
    fixture.wrap([fixture.box]).triggerDelegated(fixture.box);
    assert.strictEqual(fixture.box.hidden.value, "1");
});

check("事件委托: 点中标签时正常切换并同步隐藏域", () => {
    const fixture = createTagBox(true, "1", 3);
    const sandbox = createSandbox(fixture.$);
    sandbox.xnote.initTagSelect(fixture.box);

    fixture.wrap([fixture.box]).triggerDelegated(fixture.box.tags[1]);

    assert.strictEqual(fixture.box.tags[1].classes.indexOf("active") >= 0, true);
    assert.strictEqual(fixture.box.hidden.value, "1,2");
});

check("只读: 点击标签不改变选中态和隐藏域", () => {
    const fixture = createTagBox(true, "1", 3);
    fixture.box.attrs["data-readonly"] = "1";
    const sandbox = createSandbox(fixture.$);
    sandbox.xnote.initTagSelect(fixture.box);

    sandbox.xnote.handleTagSelectClick(fixture.box.tags[1]);

    assert.strictEqual(fixture.box.tags[1].classes.indexOf("active") >= 0, false);
    assert.strictEqual(fixture.box.hidden.value, "1");
});

console.log("\n结果: " + passed + " passed, " + failed + " failed");
process.exit(failed === 0 ? 0 : 1);
