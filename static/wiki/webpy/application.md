[目录](webpy.md)

# 初始化

# 执行

webpy的入口是入口app.run(*middleware)，这个函数很简单

>> return wsgi.runwsgi(self.wsgifunc(*middleware))

## wsgifunc

它的作用是构造符合WSGI协议的函数

>> WSGI协议很简单，形如wsgifunc(env, start_resp)，包含两个参数，一个是上下文环境env，另一个是返回函数start_resp，start_resp接受两个参数start_resp(status, headers)。wsgifunc的返回值就是HTTP协议的协议体(body部分).

wsgifunc中有一个wsgi函数，它的功能主要是3步

- 处理上下文env,转换成webapi内的内容
- 加载处理器(handle_with_processors)
- 处理程序结果

wsgifunc构造最终的WSG函数是这样的

```
for m in middleware:
    wsgi = m(wsgi)
```

middleware的结构是这样的

```
class Middleware:
    def __init__(self, app):
        self.app = app
    def __call__(self, env, start_resp):
        # do thing here
```

这样构造的wsgi函数结构如下

```
# middleware = [m1, m2]

wsgi1 = m1(wsgi)
wsgi2 = m2(wsgi1)

```
所以最终的WSGI函数是一个函数链表，越后面的优先级越高，它能优先执行并且决定是否把控制权交给前面的WSGI，这样就可以让用户自己来封装一个高于框架优先级的middleware，这也是与大多数框架所不同的地方，也是webpy强大所在。

## handle_with_processors

这个函数也是比较奇妙的

```
# processor结构
def loadhook(h):
    """
    Converts a load hook into an application processor.
    
        >>> app = auto_application()
        >>> def f(): "something done before handling request"
        ...
        >>> app.add_processor(loadhook(f))
    """
    def processor(handler):
        h()
        return handler()
        
    return processor

def unloadhook(h):
    """
    Converts an unload hook into an application processor.
    
        >>> app = auto_application()
        >>> def f(): "something done after handling request"
        ...
        >>> app.add_processor(unloadhook(f))    
    """
    def processor(handler):
        try:
            result = handler()
            is_gen = is_iter(result)
        except:
            # run the hook even when handler raises some exception
            h()
            raise

        if is_gen:
            return wrap(result)
        else:
            h()
            return result
            
    def wrap(result):
        def next_hook():
            try:
                return next(result)
            except:
                # call the hook at the and of iterator
                h()
                raise

        result = iter(result)
        while True:
            yield next_hook()
            
    return processor

class application:
    ...

    def handle_with_processors(self):
        def process(processors):
            try:
                if processors:
                    p, processors = processors[0], processors[1:]
                    return p(lambda: process(processors))
                else:
                    return self.handle()
            except web.HTTPError:
                raise
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                print(traceback.format_exc(), file=web.debug)
                raise self.internalerror()
        
        # processors must be applied in the resvere order. (??)
        return process(self.processors)
```

为什么说这个函数比较神奇呢,process这个函数使用又使用了类似于middleware结构的方式来实现一个函数序列，middleware关系到控制权的转移问题，我们可以理解写成这样，但是processors看起来无关大雅，为什么写得如此费解呢，甚至于评论都怀疑它是逆向执行的。我们仔细看看loadhook函数

- h比handler先执行
- 所以p(lambda: process(processors))这里p这个hook背后的h比lambda: process(processors)先执行，因此processors里的函数实际上是顺序执行的，那么为什么需要构造这么复杂的链表呢

构想一下，我们这样实现

```
class application:
    ...

    def handle_with_processors(self):
        try:
            for processor in self.processors:
                processor()
            return self.handle()
        except web.HTTPError:
            raise
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            print(traceback.format_exc(), file=web.debug)
            raise self.internalerror()
```

好像没什么不一样，但是仔细想想，假如发生了异常.

```
# 原本定义的3个hook
# [h1, h2, h3]
processors = [p1, p2, p3]

p1
 h1()
 # p2执行时发生了异常
 p2() # 执行p2
  h2() # 抛出异常， p2: raise self.internalerror()
  # h3 和 handler都不会被执行
 # p1也catch到异常 p1: raise self.internalerrorr()

# 改造之后的就只有一次抛出异常了
# 注意，hook没法控制其他hook的行为
```

## handle

好了，看完了处理器部分，我们来接着看看handle部分，这就是处理我们的逻辑代码的地方了

```
class application:
    ...
    def handle(self):
        fn, args = self._match(self.mapping, web.ctx.path)
        return self._delegate(fn, self.fvars, args)

    def _match(self, mapping, value):
        for pat, what in mapping:
            if isinstance(what, application):
                if value.startswith(pat):
                    f = lambda: self._delegate_sub_application(pat, what)
                    return f, None
                else:
                    continue
            elif isinstance(what, string_types):
                what, result = utils.re_subm('^' + pat + '$', what, value)
            else:
                result = utils.re_compile('^' + pat + '$').match(value)
                
            if result: # it's a match
                return what, [x for x in result.groups()]
        return None, None

    def _delegate(self, f, fvars, args=[]):
        def handle_class(cls):
            meth = web.ctx.method
            if meth == 'HEAD' and not hasattr(cls, meth):
                meth = 'GET'
            if not hasattr(cls, meth):
                raise web.nomethod(cls)
            tocall = getattr(cls(), meth)
            return tocall(*args)
            
        if f is None:
            raise web.notfound()
        elif isinstance(f, application):
            return f.handle_with_processors()
        elif isclass(f):
            return handle_class(f)
        elif isinstance(f, string_types):
            if f.startswith('redirect '):
                url = f.split(' ', 1)[1]
                if web.ctx.method == "GET":
                    x = web.ctx.env.get('QUERY_STRING', '')
                    if x:
                        url += '?' + x
                raise web.redirect(url)
            elif '.' in f:
                mod, cls = f.rsplit('.', 1)
                mod = __import__(mod, None, None, [''])
                cls = getattr(mod, cls)
            else:
                cls = fvars[f]
            return handle_class(cls)
        elif hasattr(f, '__call__'):
            return f()
        else:
            return web.notfound()

```

这部分代码就比较清晰了，handle就两件事

- 找出匹配的function，解析参数
- 执行对应的GET/POST方法

需要注意的是
- url之间出现冲突的话先定义的覆盖后定义的
- (pattern, classname) classname可以是application/class/callable或者redirect字符串 