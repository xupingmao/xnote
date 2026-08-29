/**
 * 单元测试: static/js/marked-ext.js 中的 normalizeCodeFenceLang
 *
 * 该函数定义在浏览器的 IIFE 闭包内，无法直接 require，
 * 这里从源文件中按括号配对提取函数定义，在 vm 沙箱中求值后测试。
 *
 * 运行: node tests/js/test_marked_ext.js
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const SRC = path.join(__dirname, "..", "..", "static", "js", "marked-ext.js");

function extractFunction(source, name) {
    const start = source.indexOf("function " + name + "(");
    if (start < 0) {
        throw new Error("function " + name + " not found");
    }
    let depth = 0;
    let inRegex = false;
    let inString = null;
    for (let i = start; i < source.length; i++) {
        const ch = source[i];
        if (inString) {
            if (ch === "\\") { i++; continue; }
            if (ch === inString) inString = null;
            continue;
        }
        if (inRegex) {
            if (ch === "\\") { i++; continue; }
            if (ch === "/") { inRegex = false; }
            continue;
        }
        if (ch === '"' || ch === "'" || ch === "`") { inString = ch; continue; }
        if (ch === "/") {
            if (source[i + 1] === "/") {
                while (i < source.length && source[i] !== "\n") i++;
                continue;
            }
            if (source[i + 1] === "*") {
                while (i < source.length && !(source[i] === "*" && source[i + 1] === "/")) i++;
                i++;
                continue;
            }
            // 判断是否为正则字面量: 前一个有效字符不是 ) ] } 标识符/数字/反引号
            let j = i - 1;
            while (j >= start && /\s/.test(source[j])) j--;
            const prev = j >= start ? source[j] : "";
            const isRegex = prev === "" || !/[\w)\]'"`.]/.test(prev);
            if (isRegex) { inRegex = true; continue; }
        }
        if (ch === "{") depth++;
        else if (ch === "}") {
            depth--;
            if (depth === 0) {
                return source.slice(start, i + 1);
            }
        }
    }
    throw new Error("unbalanced braces for " + name);
}

const source = fs.readFileSync(SRC, "utf8");
const sandbox = { module: {}, exports: {}, console: console };
vm.createContext(sandbox);

function loadFunction(name) {
    const fnSrc = extractFunction(source, name);
    vm.runInContext(fnSrc + "\nthis.__fn = " + name + ";", sandbox);
    return sandbox.__fn;
}

const normalizeCodeFenceLang = loadFunction("normalizeCodeFenceLang");
const preHandleBlock = loadFunction("preHandleBlock");

// ---- tiny test framework ----
let passed = 0;
let failed = 0;
function assertEqual(actual, expected, msg) {
    if (actual === expected) {
        passed++;
        console.log("  PASS: " + msg);
    } else {
        failed++;
        console.error("  FAIL: " + msg + "\n    expected: " + JSON.stringify(expected) + "\n    actual:   " + JSON.stringify(actual));
    }
}

// 场景中代码围栏前后的普通文本用于模拟真实 markdown
function wrap(fenceHead, code, fenceTail) {
    return "这是一段普通文本\n\n" + fenceHead + code + fenceTail + "\n这是另一段普通文本\n";
}

console.log("normalizeCodeFenceLang:");

// 1. 带空格的语言替换为下划线
{
    const input = wrap("```Plain Text\n", "print(1)\n", "```\n");
    const out = normalizeCodeFenceLang(input);
    assertEqual(out.includes("```Plain_Text"), true, "多词语言空格转下划线 (Plain Text -> Plain_Text)");
    assertEqual(out.includes("```Plain Text"), false, "原始带空格语言不再存在");
}

// 2. 多空格/制表符也转为下划线
{
    const input = wrap("```My   Lang\tHere\n", "x\n", "```\n");
    const out = normalizeCodeFenceLang(input);
    assertEqual(out.includes("```My_Lang_Here"), true, "连续空格与制表符转下划线");
}

// 3. 无语言标签不被修改
{
    const input = wrap("```\n", "some code\n", "```\n");
    const out = normalizeCodeFenceLang(input);
    assertEqual(out, input, "无语言围栏保持不变");
}

// 4. 单语言(无空格)保持不变
{
    const input = wrap("```python\n", "print(1)\n", "```\n");
    const out = normalizeCodeFenceLang(input);
    assertEqual(out, input, "单语言(python)保持不变");
}

// 5. 波浪号围栏同样生效
{
    const input = wrap("~~~Plain Text\n", "x\n", "~~~\n");
    const out = normalizeCodeFenceLang(input);
    assertEqual(out.includes("~~~Plain_Text"), true, "波浪号围栏语言空格转下划线");
}

// 6. 多个代码块各自处理
{
    const input = "```A B\ncode1\n```\n\n```C D\ncode2\n```\n";
    const out = normalizeCodeFenceLang(input);
    assertEqual(out.includes("```A_B") && out.includes("```C_D"), true, "多个围栏分别处理");
}

console.log("\npreHandleBlock:");

// 1. 行内公式 $...$
{
    const input = "公式 $y=f(g(x))y=f(g(x))$ 结束";
    const out = preHandleBlock(input);
    assertEqual(out, "公式 <latex>y=f(g(x))y=f(g(x))</latex> 结束", "行内公式 $...$ 转 <latex>");
}

// 2. 多个行内公式
{
    const input = "a=$x$ b=$y$";
    const out = preHandleBlock(input);
    assertEqual(out, "a=<latex>x</latex> b=<latex>y</latex>", "多个行内公式分别转换");
}

// 3. 块级 $$...$$ 不被行内规则二次处理
{
    const input = "$$a+b$$";
    const out = preHandleBlock(input);
    assertEqual(out, "<latex>a+b</latex>", "块级 $$...$$ 转 <latex>");
}

// 4. 块级公式后紧跟行内公式
{
    const input = "$$A$$ and $B$";
    const out = preHandleBlock(input);
    assertEqual(out, "<latex>A</latex> and <latex>B</latex>", "块级与行内公式共存");
}

// 5. 反斜杠定界符 \(...\) 和 \[...\]
{
    const input = "\\(x\\) and \\[y\\]";
    const out = preHandleBlock(input);
    assertEqual(out, "<latex>x</latex> and <latex>y</latex>", "\\( \\) 与 \\[ \\] 转 <latex>");
}

// 6. 行内公式内容不含 $ 或换行
{
    const out = preHandleBlock("$ok$");
    assertEqual(out, "<latex>ok</latex>", "基础行内公式");
}

console.log("\n结果: " + passed + " passed, " + failed + " failed");
process.exit(failed === 0 ? 0 : 1);
