/**
 * 单元测试: _static/js/xnote-ui/x-layout.js 中 textarea 自动高度的逻辑
 *
 * 该文件依赖浏览器环境（jQuery / DOM），这里用最小的 jQuery 桩 + 假元素在 vm 沙箱中加载，
 * 然后验证 autoResizeTextarea / initAutoResizeTextarea 的行为。
 *
 * 运行: node tests/js/test_auto_resize_textarea.js
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");

const SRC = path.join(__dirname, "..", "..", "_static", "js", "xnote-ui", "x-layout.js");

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

function createElement(initialHeight) {
    return {
        style: {},
        scrollHeight: 0,
        clientHeight: initialHeight || 0,
        events: {},
    };
}

function createWrapper(list) {
    const wrapper = {
        length: list.length,
        each: function (fn) {
            for (let i = 0; i < list.length; i++) {
                fn.call(list[i], i, list[i]);
            }
            return wrapper;
        },
        height: function (value) {
            if (value === undefined) {
                return list[0].clientHeight;
            }
            for (let i = 0; i < list.length; i++) {
                list[i].style.height = value + "px";
            }
            return wrapper;
        },
        css: function (name, value) {
            for (let i = 0; i < list.length; i++) {
                list[i].style[name] = value;
            }
            return wrapper;
        },
        on: function (event, fn) {
            for (let i = 0; i < list.length; i++) {
                const elem = list[i];
                if (!elem.events[event]) {
                    elem.events[event] = [];
                }
                elem.events[event].push(fn);
            }
            return wrapper;
        },
    };
    return wrapper;
}

function createSandbox(elements) {
    const $ = function (arg) {
        if (typeof arg === "string") {
            return createWrapper(elements);
        }
        return createWrapper([arg]);
    };
    $.fn = {};
    const sandbox = { $: $, xnote: { layout: {} }, console: console };
    vm.runInNewContext(fs.readFileSync(SRC, "utf8"), sandbox, { filename: SRC });
    return sandbox;
}

check("autoResizeTextarea: 测量前先把高度重置为 auto，再按 scrollHeight 设置", () => {
    const elem = createElement();
    let heightWhenMeasure = null;
    Object.defineProperty(elem, "scrollHeight", {
        get: function () {
            heightWhenMeasure = elem.style.height;
            return 120;
        },
    });

    const sandbox = createSandbox([elem]);
    sandbox.xnote.layout.autoResizeTextarea(elem);

    assert.strictEqual(heightWhenMeasure, "auto");
    assert.strictEqual(elem.style.height, "120px");
});

check("initAutoResizeTextarea: rows 渲染出的高度作为 min-height，初始高度按内容计算", () => {
    const elem = createElement(60);
    const sandbox = createSandbox([elem]);
    sandbox.xnote.layout.getTextareaTextHeight = function () {
        return 90;
    };

    sandbox.xnote.layout.initAutoResizeTextarea(".x-form textarea");

    assert.strictEqual(elem.style["min-height"], "60px");
    assert.strictEqual(elem.style.height, "90px");
    assert.strictEqual(elem.events.input.length, 1);
});

check("initAutoResizeTextarea: 输入后高度跟随内容变化（可增可减）", () => {
    const elem = createElement(60);
    const sandbox = createSandbox([elem]);
    sandbox.xnote.layout.getTextareaTextHeight = function () {
        return 60;
    };
    sandbox.xnote.layout.initAutoResizeTextarea(".x-form textarea");

    elem.scrollHeight = 150;
    elem.events.input[0]();
    assert.strictEqual(elem.style.height, "150px");

    elem.scrollHeight = 30;
    elem.events.input[0]();
    assert.strictEqual(elem.style.height, "30px");
});

console.log("\n结果: " + passed + " passed, " + failed + " failed");
process.exit(failed === 0 ? 0 : 1);
