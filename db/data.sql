
-- Since 2016/06
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
smtime text,
satime text,
sctime text,
related text,
-- type text default 'text', this is not a requirement, related can do it's work
visited_cnt int default 0,
is_deleted int default 0);


-- ÐÂÔö×Ö¶Î²Ù×÷
-- Now 2016-12-04

