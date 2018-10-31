"""

"""

__all__ = ['named_tuple']


def named_tuple(*names):
    class NameTuple(tuple):
        __names = {name: index for index, name in enumerate(names)}

        def __new__(cls, *args):
            return tuple.__new__(cls, args)

        def __getattr__(self, item):
            return self[NameTuple.__names[item]]

        def __repr__(self):
            return str(dict(zip(names, self)))

    return NameTuple


if __name__ == '__main__' and 1:
    Point = named_tuple('x', 'y')
    p = Point(1, 2)
    print(p.x, p.y)  # 1 2


    class Array(named_tuple('x', 'y', 'z')):
        def x(self):
            return '能通过类绑定访问'

        @property
        def y(self):
            return 'Y的值'


    array = Array(100, 200, 300)
    print(array.x)  # <bound method Array.x of (100, 200, 300)>
    print(Array.x(array))  # 能通过类绑定访问
    print(array.y)  # Y的值
    print(array.z)  # Y的值
