# xnote插件

## 新增插件

点击菜单的【插件】-> 【新增插件】，然后在新增插件页面输入插件名称。（新增插件功能本身就是用插件机制实现的）

## 插件示例

```python
import xutils
from xtemplate import BasePlugin

class Main(BasePlugin):
    """默认的插件声明入口，定义一个叫做Main的类"""
    
    title = '测试插件'

    def render(self):
        # 处理页面渲染
        name = xutils.get_argument("name", "defaultName")
        return "Hello, %s" % name
        
    def command(self, input):
        # 处理命令请求
        pass
```

## 插件卸载

直接删除对应的Python文件即可

## 插件的生命周期

- 初始化：系统启动或者刷新的时候触发
- 响应客户请求：执行render方法
- 系统关闭：暂时无