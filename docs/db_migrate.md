# 2.3版本及以上

系统自动升级数据

# 1.3版本到2.2版本

sqlite到leveldb迁移

> 适用于2.3版本以下升级到2.3版本

2.3版本开始，出于性能和扩展性的考虑，xnote的数据存储从sqlite切换成leveldb。

在【系统】页面找到【数据迁移】功能。再执行相关的迁移操作即可，注意如果数据量比较大可能迁移时间比较长。

# 1.2版本之前

## sqlite老版本迁移

如果启动失败，报数据库字段错误、或者是启动成功但是丢失了资料的日期信息，那么可能是安装了早期版本导致的，需要对数据库进行一次手动升级，由于sqlite不支持字段重命名，所以会略微麻烦一些。

升级工作主要是三步，如下所示，需要说明的是备份可以登陆到服务器使用sqlite安装程序，也可以通过关键字`sql`搜索出xnote自带的工具操作

- 备份`file`表,

```sql
alter table file rename to file_20171124;
```

- 创建新的`file`表，这一步可以通过重新启动xnote来自动创建
- 把备份数据迁移到新的`file`表中

```sql
insert into file ( id, name, content, data, size, version, type, 
parent_id, related, ctime, mtime, atime, visited_cnt, is_deleted, is_public, is_marked,
creator, modifier, groups, priority) 

select id, name, content, data, size, version, type, 
parent_id, related, sctime, smtime, satime, visited_cnt, is_deleted, is_public, is_marked,
creator, modifier, groups, priority from file_20171124;

```

## message表删除字段

```sql
-- 重命名表名
ALTER TABLE message rename TO message_old;

-- 移动部分字段到新表
INSERT INTO message (id, ctime, mtime, user, status, content)
SELECT id, ctime, mtime, user, status, content FROM message_old;

-- 如果OK，删除旧表
```
