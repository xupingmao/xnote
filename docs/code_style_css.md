# CSS代码规范

* 不建议使用ID选择器
* `*-style`用于解决命名冲突问题，不设定任何独立的样式
* 使用横线`-`而不是下划线`_`
    - 正例: `tab-box`
    - 反例: `tab_box`
* 建议使用多个class组合而不是一个长class
    - 正例: `tag red`，如果`red`冲突了可以使用`tag red-style`
    - 反例: `red-tag`
    - 特殊情况: 名称冲突时使用长名称
* 类型放在后面
* 常用的命名
    - 导航: `nav`
    - 页头: `header`
    - 页脚: `footer`
    - 容器: `container`, `box`