# encoding=utf-8

import unittest

from xutils.markdown_util import has_latex


class TestHasLatex(unittest.TestCase):

    def test_block_dollar(self):
        # 块级 $$...$$ 公式
        self.assertTrue(has_latex("$$\frac{a}{b}$$"))

    def test_inline_dollar(self):
        # 行内 $...$ 公式
        self.assertTrue(has_latex("损失 $L=\\frac12$ 很小"))

    def test_block_dollar_multiline(self):
        # 块级公式可跨行
        text = "$$\n\\begin{aligned}\nz_1 &= w_1 x\n\\end{aligned}\n$$"
        self.assertTrue(has_latex(text))

    def test_code_fence_latex(self):
        # 代码围栏 ```latex
        text = "```latex\nx\n```"
        self.assertTrue(has_latex(text))

    def test_escape_paren(self):
        # \( \) 定界
        self.assertTrue(has_latex("\\(\\boldsymbol x\\)"))

    def test_escape_bracket(self):
        # \[ \] 定界
        self.assertTrue(has_latex("\\[\\sum x\\]"))

    def test_no_formula_plain_text(self):
        # 普通文本不含公式
        self.assertFalse(has_latex("今天天气不错，去学习一下"))

    def test_single_dollar_is_not_formula(self):
        # 单个 $ 符号（如价格）不应误判为公式
        self.assertFalse(has_latex("它只要 $5 而已"))

    def test_dollar_sign_escaped(self):
        # 转义的 \$ 不应被当作公式定界
        self.assertFalse(has_latex("售价是 \\$5 和 \\$10"))


if __name__ == "__main__":
    unittest.main()
