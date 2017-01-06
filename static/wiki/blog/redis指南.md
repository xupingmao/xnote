# 目录

- [配置命令](#配置命令)
- [分布式锁](#分布式锁)
- [分布式事务](#分布式事务)

## 配置命令

- 连接
```
redis-cli -h host -p port -a pswd
```

- 选择db
<pre>
select 2
</pre>


## 分布式锁

- setnx(key,value)
<pre>
setnx(key, value) 
</pre>

## 分布式事务

- MULTI
<pre>
>>> MULTI
>>> DO SOMETHING
>>> EXEC
执行结果
</pre>
- WATCH
