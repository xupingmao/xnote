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
// preHandleBlock 依赖同作用域的 stripLatexDelims，注入为沙箱全局供其调用
sandbox.stripLatexDelims = loadFunction("stripLatexDelims");
const preHandleBlock = loadFunction("preHandleBlock");

// 提取对象方法(如 myRenderer.html = function ...)，用于在沙箱中求值后测试
function extractMethod(src, objName, methodName) {
    const marker = objName + "." + methodName + " = function";
    const start = src.indexOf(marker);
    if (start < 0) throw new Error(marker + " not found");
    const fnStart = src.indexOf("function", start);
    let depth = 0, inRegex = false, inString = null;
    for (let i = fnStart; i < src.length; i++) {
        const ch = src[i];
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
            if (src[i + 1] === "/") { while (i < src.length && src[i] !== "\n") i++; continue; }
            if (src[i + 1] === "*") { while (i < src.length && !(src[i] === "*" && src[i + 1] === "/")) i++; i++; continue; }
            let j = i - 1;
            while (j >= fnStart && /\s/.test(src[j])) j--;
            const prev = j >= fnStart ? src[j] : "";
            if (prev === "" || !/[\w)\]'"`.]/.test(prev)) { inRegex = true; continue; }
        }
        if (ch === "{") depth++;
        else if (ch === "}") { depth--; if (depth === 0) return src.slice(fnStart, i + 1); }
    }
    throw new Error("unbalanced braces for " + objName + "." + methodName);
}
function loadMethod(objName, methodName) {
    const fnSrc = extractMethod(source, objName, methodName);
    vm.runInContext("this.__fn = " + fnSrc + ";", sandbox);
    return sandbox.__fn;
}
const myRenderer_html = loadMethod("myRenderer", "html");

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

console.log("\npreHandleBlock (复杂公式混排回归):");

// 复现用户上报的多公式混排输入(含 $...$ / $$...$$ / \(...\) / \[...\] 以及 $$ 内嵌套 \(...\))
const complexInput = [
    '复合函数 $\\(y=f(g(x))\\)$',
    '$$\\frac{\\partial y}{\\partial x}=\\frac{\\partial y}{\\partial g}\\cdot\\frac{\\partial g}{\\partial x}$$',
    '多层神经网络就是一串复合函数，反向传播就是把链式法则从后往前算一遍。',
    '',
    '举个极简两层网络：',
    '$$',
    '\\\\(\\boldsymbol b\\)egin{aligned}',
    'z_1 &= w_1 x + \\(\\boldsymbol b\\)_1 \\\\',
    'a_1 &= \\text{ReLU}(z_1) \\\\',
    'z_2 &= w_2 a_1 + \\(\\boldsymbol b\\)_2 \\\\',
    '\\hat y &= z_2',
    '\\end{aligned}',
    '$$',
    '损失用 MSE：$L=\\frac12(\\hat y - y)^2$',
    '',
    '我们想求：$\\dfrac{\\partial L}{\\partial w_2},\\dfrac{\\partial L}{\\partial \\(\\boldsymbol b\\)_2},\\dfrac{\\partial L}{\\partial w_1},\\dfrac{\\partial L}{\\partial \\(\\boldsymbol b\\)_1}$',
    ''
].join("\n");

const complexOut = preHandleBlock(complexInput);

// 1. 不再把整段合并成一个巨型公式导致 "解析失败"
assertEqual(complexOut.indexOf("解析失败") >= 0, false, "复杂混排不再出现解析失败拼接");

// 2. 反斜杠公式命令保留(如 \\frac \\boldsymbol \\text)
assertEqual(complexOut.indexOf("\\frac") >= 0, true, "反斜杠公式命令(\\frac)被保留");
assertEqual(complexOut.indexOf("\\boldsymbol") >= 0, true, "反斜杠公式命令(\\boldsymbol)被保留");
assertEqual(complexOut.indexOf("\\text") >= 0, true, "\\text 被保留");

// 3. 每个公式被独立包成 <latex>，且不跨边界合并
{
    const tags = (complexOut.match(/<latex>/g) || []).length;
    assertEqual(tags >= 4, true, "多个公式各自独立包成 <latex> (count=" + tags + ")");
}

// 4. $$ 内部的 \(...\) 定界符被剥离(避免重复定界导致 KaTeX 失败)
assertEqual(complexOut.indexOf("\\(\\boldsymbol") >= 0, false, "$$ 内部的 \\( 冗余定界符已剥离");

console.log("\nmyRenderer.html (HTML 净化 / DOMPurify 降级):");

// 沙箱默认没有 window -> 走正则降级分支
assertEqual(myRenderer_html('<script>alert(1)</script>'), "", "降级: 去除 <script>");
assertEqual(myRenderer_html('<div><script>x</script></div>'), "", "降级: 嵌套 <script> 整段丢弃");
assertEqual(myRenderer_html('<script/>'), "", "降级: 自闭合 <script> 去除");
assertEqual(myRenderer_html('<latex>a+b</latex>'), "<latex>a+b</latex>", "降级: 保留 <latex>");
assertEqual(myRenderer_html('<div>hi</div>'), "<div>hi</div>", "降级: 普通标签保留");

// 注入 window.DOMPurify -> 走 DOMPurify 分支
{
    let captured = null;
    sandbox.window = {
        DOMPurify: {
            sanitize: function (html, cfg) {
                captured = { html: html, cfg: cfg };
                // mock: 去除 script，保留其余(含 latex)
                return html.replace(/<script[\s\S]*?<\/script>/gi, "");
            }
        }
    };
    const out = myRenderer_html('<div><script>x</script></div>');
    assertEqual(out, "<div></div>", "DOMPurify: 去除 script 保留外层");
    assertEqual(captured.cfg.ADD_TAGS.indexOf("latex") >= 0, true, "DOMPurify: 配置保留 latex 标签");
    assertEqual(captured.cfg.FORBID_TAGS.indexOf("pre") >= 0, true, "DOMPurify: 配置禁用 pre 标签");
    delete sandbox.window;
}

console.log("\n结果: " + passed + " passed, " + failed + " failed");
process.exit(failed === 0 ? 0 : 1);
