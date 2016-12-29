# utils.py

## overview

- webpy中的类首字母大小写均可

## storage

- 同时具备dict/object的特性，也就是可以用`.`或者`[]`访问
- 继承dict，重写了`__getattr__`, `__setattr__`, `__delattr__`这三个方法

## storify

- return Storage