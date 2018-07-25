可以进行结构化查询的仿字典

* 例1: 没有主键的字典创建,索引的创建,域的添加和删除
```python
db = SQDict(v1=None, v2=None)
db.create_indexes('v1')

db.insert(v2=2)
db.insert(v2=2)
db.create_indexes('v1')

try:
    db.create_indexes('x')
except AttributeError as e:
    print(e)  # 'Record' object has no attribute 'x'

db.print()
# =====================
# <id>   |v1     |v2
# ---------------------
# 0      |None   |2
# 1      |None   |2
# =====================

db.add_field('x', 'NewField')
db.create_indexes('x')
db.print()
# ====================================
# <id>    |v1      |v2      |x
# ------------------------------------
# 0       |None    |2       |NewField
# 1       |None    |2       |NewField
# ====================================

db.drop_field('x')
db.print()
# ===========================
# <id>    |v1      |v2
# ---------------------------
# 0       |None    |2
# 1       |None    |2
# ===========================
```

* 例2: 只有一个主键的字典创建, 记录的修改, 域的提取
```python
db = SQDict('k1', v1=None, v2=None)  # 创建时 *args 对应主键, **kwargs 对视为值域, 值域必须有默认值

db.insert('A', v1=1, v2=2)  # 插入时 *args 对应主键项, **kwargs 对应值域
db.create_indexes('k1', 'v1')  # 主键或值域都能建立索引

try:
    db.insert('A', k1='A1')  # 不能在 **kwargs 中再去修改主键
except AttributeError as e:
    print(e)  # 'Record' object attribute 'k1' is read-only

try:
    db.insert(v2=2)  # 如果设置了主键, 插入时没有 *args 参数, 会抛出 TypeError
except TypeError as e:
    print(e)  # <__main__.SQDict object at 0x04DBC8F0>.insert expect 1 keys, got 0

r = db['A']
r <<= {'v1': 11}  # 修改记录

db['B'] = {'v1': 10, 'v2': 20}  # 插入新记录
del db['A']

for r in db:
    print(r >> db.fields)  # 在记录中提取域
# {'k1': 'B', 'v1': 10, 'v2': 20}

try:
    db.drop_field('k1')
except AttributeError as e:
    print(e)  # 'Record' object attribute 'k1' is read-only
```

* 例3:多个主键的表创建, 结构化查询, 文件的保存与加载
```python
db = SQDict('id', 'name', age=18, city='<Unknown>')
db.create_indexes('age', 'city')

db[10000, 'Zhang'] = {'age': 21, 'city': 'BJ'}
db[10001, 'Zhang'] = {'age': 21}
db[10002, 'Zhang'] = {'age': 25}
db[10003, 'Wang'] = {'age': 20, 'city': 'SH'}
db[10004, 'Li'] = {'city': 'GZ'}

# 所有 query 条件都为 and 关系, 需要 or 关系请执行多个 query 语句再将结果并联
rs = db.query(id=lambda v: 10000 <= v <= 10002, name='Zhang', age=21, city=lambda v: v in ('BJ', 'SH'))
print(list(rs))  # [(10000, 'Zhang', 21, 'BJ')]

db.save('db.pickle')

db2 = SQDict.load('db.pickle')
db2.print()
# =========================================
# <id>   |id     |name   |age    |city
# -----------------------------------------
# 0      |10000  |Zhang  |21     |BJ
# 1      |10001  |Zhang  |21     |<Unknown>
# 2      |10002  |Zhang  |25     |<Unknown>
# 3      |10003  |Wang   |20     |SH
# 4      |10004  |Li     |18     |GZ
# =========================================

rs = db2.query(age=18, city='NewYork')
print(list(rs))  # []

rs = db2.query(age=lambda v: v < 0)
print(list(rs))  # []

rs = db2.query(name='')
print(list(rs))  # []

rs = db2.query(name=lambda v: v == '')
print(list(rs))  # []
```
