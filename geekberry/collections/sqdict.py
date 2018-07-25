import pickle
import itertools

__all__ = ['SQDict']


class Record:
    __sqdict = None
    __index = None
    __primaries = None

    def __init__(self, sqdict: 'SQDict', index: int, keys: tuple, value_dict: dict):
        # 添加三个属性占位
        super().__setattr__(f'_{self.__class__.__name__}__sqdict', sqdict)
        super().__setattr__(f'_{self.__class__.__name__}__index', index)
        super().__setattr__(f'_{self.__class__.__name__}__primaries', ())  # 将主键置空, 以便能在 __setattr__ 中修改主键域

        # 对主键直接进行赋值
        for field, value in zip(sqdict.primaries, keys):
            self.__setattr__(field, value)
        self.__primaries = sqdict.primaries  # 对主键域进行更新, 再给值域赋值

        # 必须按照 sqdict.value_dict 的顺序设置属性
        for field in sqdict.value_dict:
            try:
                value = value_dict[field]
            except KeyError:
                value = sqdict.value_dict[field]
            self.__setattr__(field, value)

    def __iter__(self):
        return itertools.islice(self.__dict__.values(), 3, None)  # 跳过前 3 个私有属性[__sqdict, __index, __primaries]

    def __setattr__(self, field: str, value):
        if field in self.__primaries:
            raise AttributeError(f"'{self.__class__.__name__}' object attribute '{field}' is read-only")

        if hasattr(self, field):
            self.__sqdict._discard_indexed(field, getattr(self, field), self.__index)
        super().__setattr__(field, value)
        self.__sqdict._add_indexed(field, value, self.__index)

    def __delattr__(self, field):
        if field in self.__primaries:
            raise AttributeError(f"'{self.__class__.__name__}' object attribute '{field}' is read-only")

        if hasattr(self, field):
            self.__sqdict._discard_indexed(field, getattr(self, field), self.__index)
        super().__delattr__(field)

    def __lshift__(self, value_dict: dict) -> 'Record':  # insert or update
        for field, value in value_dict.items():
            self.__setattr__(field, value)
        return self

    def __rshift__(self, fields: tuple) -> dict:  # select fields
        return {field: getattr(self, field) for field in fields}

    def __repr__(self):
        return self.__class__.__name__ + str(tuple(self))


class UniversalSet:
    """ 全集, 对集合进行与操作时, 避免第一次的与操作, 直接返回 other """

    def __init__(self, universal_set):
        self.__universal = True
        self.__set = universal_set

    def __bool__(self):
        return bool(self.__set)

    def __iter__(self):
        return iter(self.__set)

    def __and__(self, other: set):
        if self.__universal:  # universal & set(...) => set(...)
            self.__universal = False
            self.__set = other
        elif other is None:  # UniversalSet & None => set()
            self.__set.clear()
        else:
            self.__set &= other
        return self


class SQDict:
    def __init__(self, *primaries, **value_dict):
        self.primaries = primaries
        self.value_dict = value_dict

        self.__index_iter = itertools.count()
        self.__indexed_table = {}  # {field:{value:set(index, ...), ...}, ...}
        self.__key_index_map = {}  # {key:index, ...}
        self.__record_table = {}  # {index:Record, ...}

    @property
    def fields(self) -> tuple:
        return self.primaries + tuple(self.value_dict.keys())

    @property
    def indexed_fields(self):
        return self.__indexed_table.keys()

    def __iter__(self):
        return iter(self.__record_table.values())

    def __setitem__(self, keys, value_dict: dict):
        assert isinstance(value_dict, dict)
        if len(self.primaries) == 1:
            keys = (keys,)
        self.insert(*keys, **value_dict)

    def __getitem__(self, keys):
        if len(self.primaries) == 1:
            keys = (keys,)
        index = self.__key_index_map[keys]
        return self.__record_table[index]

    def __delitem__(self, keys):
        if len(self.primaries) == 1:
            keys = (keys,)
        index = self.__key_index_map.pop(keys)
        record = self.__record_table.pop(index)
        for field in self.indexed_fields:  # 去除所有索引
            value = getattr(record, field)
            self._discard_indexed(field, value, index)

    # -------------------------------------------------------------------------
    def create_indexes(self, *fields) -> None:
        for field in fields:
            if field not in self.fields:
                raise AttributeError(f"'{Record.__name__}' object has no attribute '{field}'")
            elif field in self.__indexed_table:
                break  # 已有索引记录, 或非
            else:
                self.__indexed_table[field] = {}
                for index, record in self.__record_table.items():
                    self._add_indexed(field, getattr(record, field), index)

    def delete_index(self, field):
        if field in self.__indexed_table:
            del self.__indexed_table[field]

    def add_field(self, field, value):
        # 先对已有记录添加域和值
        for record in self:
            setattr(record, field, value)
        # 再更新默认值域
        self.value_dict[field] = value

    def drop_field(self, field):
        for record in self:
            delattr(record, field)

        self.delete_index(field)
        self.value_dict.__delitem__(field)

    def insert(self, *keys, **value_dict) -> None:
        if len(keys) != len(self.primaries):
            raise TypeError(f'{self}.insert expect {len(self.primaries)} keys, got {len(keys)}')

        index = self.__key_index_map.get(keys)
        if index is None:  # insert
            index = next(self.__index_iter)
            self.__record_table[index] = Record(self, index, keys, value_dict)
            if len(keys):  # 只对有主键的表填写 key_index_map
                self.__key_index_map[keys] = index
        else:  # update
            self.__record_table[index] <<= value_dict

    # -------------------------------------------------------------------------
    def _add_indexed(self, field: str, value, index: int) -> None:
        entry = self.__indexed_table.get(field)
        if entry is None:
            return

        index_set = entry.get(value)
        if index_set is None:
            entry[value] = {index}
        else:
            index_set.add(index)

    def _discard_indexed(self, field: str, value, index: int) -> None:
        entry = self.__indexed_table.get(field)
        if entry is None:
            return

        index_set = entry.get(value)
        if index_set is None:
            return

        index_set.discard(index)
        if not index_set:  # 去除空集合
            entry.__delitem__(value)

    # -------------------------------------------------------------------------
    def query(self, **condition_dict) -> iter:
        indexed_value = []
        indexed_callable = []
        no_indexed = {}

        for field, condition in condition_dict.items():
            if field in self.indexed_fields:
                if callable(condition):
                    indexed_callable.append((field, condition))
                else:
                    indexed_value.append((field, condition))
            else:
                no_indexed[field] = condition

        # -----------------------------------------------------
        index_set = UniversalSet(self.__record_table.keys())

        # 索引项 + 立即数
        for field, value in indexed_value:
            index_set &= self.__indexed_table[field].get(value)
            if not index_set:
                raise StopIteration

        # 索引项 + 条件函数
        for field, condition in indexed_callable:
            entry = self.__indexed_table[field]

            found_index_set = set()
            for value in filter(condition, entry):
                found_index_set.update(entry[value])

            index_set &= found_index_set
            if not index_set:
                raise StopIteration

        # 非索引项
        for index in index_set:
            record = self.__record_table[index]
            if self.match(record, **no_indexed):
                yield record

    @staticmethod
    def match(record: Record, **condition_dict) -> bool:
        for field, condition in condition_dict.items():
            if callable(condition):
                if not condition(getattr(record, field)):
                    return False
            else:
                if not (getattr(record, field) == condition):  # 注意 getattr 放在前面, 以适用 __eq__ 重载
                    return False

        return True

    # =========================================================================
    @staticmethod
    def load(filename: str) -> 'SQDict':
        with open(filename, 'rb') as file:
            return pickle.load(file)

    def save(self, filename: str) -> None:
        with open(filename, 'wb') as file:
            pickle.dump(self, file)

    # =========================================================================
    def print(self, w: int = 8) -> None:
        ww = w + 1

        heads = map(str, ['<id>'] + list(self.fields))
        heads = [s.ljust(w) for s in heads]

        print('\n', self)
        print('=' * ww * len(heads))
        print('|'.join(heads))
        print('-' * ww * len(heads))
        for index, record in self.__record_table.items():
            lines = map(str, [index] + list(record))
            lines = [s.ljust(w) for s in lines]
            print('|'.join(lines))
        print('=' * ww * len(heads))

        # 调试用
        # print('key_index_map:', self.__key_index_map)
        # print('indexed_table:', self.__indexed_table, '\n')


if __name__ == '__main__' and 0:
    # 没有主键的情况
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

if __name__ == '__main__' and 0:
    # 只有一个主键, 中途创建索引
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

if __name__ == '__main__' and 0:
    # 有多个主键, 数据库的保存和加载
    db = SQDict('id', 'name', age=18, city='<Unknown>')
    db.create_indexes('age', 'city')

    db[10000, 'Zhang'] = {'age': 21, 'city': 'BJ'}
    db[10001, 'Zhang'] = {'age': 21}
    db[10002, 'Zhang'] = {'age': 25}
    db[10003, 'Wang'] = {'age': 20, 'city': 'SH'}
    db[10004, 'Li'] = {'city': 'GZ'}

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
