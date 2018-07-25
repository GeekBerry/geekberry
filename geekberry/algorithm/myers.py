"""
参考资料:
    [从DiffUtil到Myers'差分算法](https://www.jianshu.com/p/7f1473c2e521)
    [Git是怎样生成diff的：Myers算法](http://cjting.me/misc/how-git-generate-diff/)
    [The Myers diff algorithm](https://blog.jcoglan.com/2017/02/12/the-myers-diff-algorithm-part-1/)
    [An O(ND) Difference Algorithm and Its Variations](http://www.xmailserver.org/diff2.pdf)
"""

from copy import deepcopy
from itertools import repeat

__all__ = ['meyer', 'Add', 'Equ', 'Sub']


class Action:
    OPERATE_MAP = {'Add': '+', 'Equ': '=', 'Sub': '-'}
    priority = None
    count = 1

    @property
    def operate(self):
        return self.OPERATE_MAP.get(self.__class__.__name__)

    def inc(self):
        self.count += 1

    def __len__(self):
        return self.count

    def __str__(self):
        return self.operate * self.count


class Add(Action):
    priority = 1


class Equ(Action):
    priority = 0


class Sub(Action):
    priority = -1


class Snake(list):
    HEAD = Action()

    @property
    def tail(self):
        return self[-1] if self else Snake.HEAD

    def push(self, action_type):
        if type(self.tail) is action_type:
            self.tail.inc()
        else:
            super().append(action_type())

    def __str__(self):
        return ''.join(map(str, self))


class Node:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y
        self.snake = Snake()

    @property
    def k(self):
        return self.x - self.y

    def __hash__(self):
        return self.k

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def inner(self, other):
        return self.x <= other.x and self.y <= other.y

    def add(self):
        node = deepcopy(self)
        node.y += 1
        node.snake.push(Add)
        return node

    def sub(self):
        n = deepcopy(self)
        n.x += 1
        n.snake.push(Sub)
        return n

    def forward(self, old, new):
        while self.x < len(old) and self.y < len(new) and old[self.x] == new[self.y]:
            self.x += 1
            self.y += 1
            self.snake.push(Equ)

    def __repr__(self):
        return f'({self.x}, {self.y})'


class RecordList(list):
    def __init__(self, end: Node):
        super().__init__(repeat(None, end.x + end.y + 1))
        self.end = end

    def iter(self, deep):
        left = max(-deep, -self.end.y)
        left += (left ^ deep) & 1

        right = min(deep, self.end.x)
        right -= (right ^ deep) & 1

        for i in range(left, right + 1, 2):  # +1 取闭区间
            node = self[i]
            if node is not None:
                yield node

    def push(self, node):
        if node.inner(self.end):
            record = self[node.k]
            if not record:
                self[node.k] = node
            elif node.x > record.x:
                self[node.k] = node
            elif node.x < record.x:
                return
            elif node.snake.tail.priority > record.snake.tail.priority:
                self[node.k] = node

    def __repr__(self):
        string = ','.join(map(lambda each: ' ' * 6 if each is None else str(each), self))
        return f'(-{self.end.y}, {self.end.x}){string}'


def meyer(old, new) -> Snake:
    end = Node(len(old), len(new))

    node_list = RecordList(end)
    node_list[0] = Node()

    for deep in range(len(node_list)):
        for node in node_list.iter(deep):
            if node == end:
                return node.snake
            node.forward(old, new)
            node_list.push(node.sub())
            node_list.push(node.add())


if __name__ == '__main__':
    old = 'ABCABBA'
    new = 'CBABAC'

    snake = meyer(old, new)
    print(snake)

    for a in snake:
        print(type(a), len(a))
