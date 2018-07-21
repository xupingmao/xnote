# xnote插件

## 插件示例

```python
import xutils
from xtemplate import BaseTextPlugin

class Main(BaseTextPlugin):
    """默认的插件声明入口，定义一个叫做Main的类"""

    def render(self):
        # 处理页面渲染
        name = xutils.get_argument("name", "defaultName")
        return "Hello, %s" % name
        
    def command(self, input):
        # 处理命令请求
        pass
```