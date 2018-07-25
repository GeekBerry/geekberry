"""

"""

__all__ = ['named_tuple']


def named_tuple(*names) -> 'class':
    if len(names) != len(set(names)):
        return TypeError(f'have repeated name in {names}')

    class NamedTuple(tuple):
        def __new__(cls, *args):
            if len(args) != len(names):
                raise TypeError(f'{cls.__name__}.__new__ require {len(names)} arguments, got {len(args)}')

            return tuple.__new__(cls, args)

        def __getattribute__(self, item):
            try:  # 优先获取 names
                index = names.index(item)
            except ValueError:  # 没在 names
                return super().__getattribute__(item)  # 尝试获取属性
            else:
                return self[index]

    return NamedTuple


if __name__ == '__main__' and 0:
    Point = named_tuple('x', 'y')
    p = Point(1, 2)
    print(p.x, p.y)  # 1 2


    class Array(named_tuple('x', 'y', 'z')):
        def x(self):  # 该属性会被覆盖
            return '只能通过类绑定访问'

        @property
        def y(self):
            return '该值不能被访问'

        def get_z(self):
            return self.z


    array = Array(100, 200, 300)
    print(array.x)  # 100
    print(Array.x(array))  # 通过类绑定才能访问
    print(array.y)  # 200
    print(array.get_z())  # 300
