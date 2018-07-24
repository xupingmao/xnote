# xnote插件

## 新增插件

在```$DATA/scripts/plugins```目录下创建一个Python文件。

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

## 插件卸载

直接删除对应的Python文件即可