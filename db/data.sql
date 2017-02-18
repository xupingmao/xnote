
-- Since 2016/06
-- name 唯一，参考大部分博客和wiki系统，暂时不设置多级目录
-- 如果有需要，可以自己通过在文件中加入链接来维护目录
-- 所有的URI也直接以资料名命名
-- 所有字段都是可读的
create table if not exists `file` (
id integer primary key autoincrement,
name text,  
content text,
path text, -- for local file
parent_id int default 0, -- for hierarchical filesystem
children text, -- children
-- bin blob, -- for binary data
size long,
-- mtime long, -- seconds
-- atime long, -- seconds
-- ctime long, -- seconds
type text,
smtime text,
satime text,
sctime text,
related text,
-- type text default 'text', this is not a requirement, related can do it's work
visited_cnt int default 0,
is_deleted int default 0,
creator text,
groups text);


-- 当前时间
-- Now 2016-12-04

