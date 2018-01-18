# 数据库迁移

如果启动失败，报数据库字段错误、或者是启动成功但是丢失了资料的日期信息，那么可能是安装了早期版本导致的，需要对数据库进行一次手动升级，由于sqlite不支持字段重命名，所以会略微麻烦一些。

升级工作主要是三步，如下所示，需要说明的是备份可以登陆到服务器使用sqlite安装程序，也可以通过关键字`sql`搜索出xnote自带的工具操作

- 备份`file`表,

```
alter table file rename to file_20171124;
```

- 创建新的`file`表，这一步可以通过重新启动xnote来自动创建
- 把备份数据迁移到新的`file`表中

```
insert into file ( id, name, content, data, size, version, type, 
parent_id, related, ctime, mtime, atime, visited_cnt, is_deleted, is_public, is_marked,
creator, modifier, groups, priority) 
select id, name, content, data, size, version, type, 
parent_id, related, sctime, smtime, satime, visited_cnt, is_deleted, is_public, is_marked,
creator, modifier, groups, priority from file_20171124;

```