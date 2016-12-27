# 分组排序

```
select a.id,a.country,a.name,a.score from tb_score a   
where   
(select count(*) from tb_score where country = a.country and score > a.score )<3  
order by a.country,score DESC;  
```