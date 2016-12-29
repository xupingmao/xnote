# webapi.py

## 注意
- webapi很多方法是基于ThreadLocal的,所以参数并没有带上上下文
- 在多线程的情况下可以放心调用不用担心污染问题

## HTTPError

- \__init__(status,headers={},data="")


## rawinput(method=None)

- 原始的参数

## input(\*requireds, **defaults)

- 返回结构[storify](utils.md#storify)
- 返回请求参数

## data()

- 返回原始的请求数据(str/byte?)

## debug(*args)

- ```Prints a prettyprinted version of `args` to stderr.```
- 打印调试信息

## setcookie

```
def setcookie(name, value, expires='', domain=None,
              secure=False, httponly=False, path=None)
```

## cookies

```
def cookies(*requireds, **defaults)
```