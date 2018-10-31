"""
参考资料:
    [从DiffUtil到Myers'差分算法](https://www.jianshu.com/p/7f1473c2e521)
    [Git是怎样生成diff的：Myers算法](http://cjting.me/misc/how-git-generate-diff/)
    [The Myers diff algorithm](https://blog.jcoglan.com/2017/02/12/the-myers-diff-algorithm-part-1/)
    [An O(ND) Difference Algorithm and Its Variations](http://www.xmailserver.org/diff2.pdf)
"""
from itertools import repeat

__all__ = ['DEL', 'PASS', 'ADD', 'myers', 'diff']

DEL, PASS, ADD = -1, 0, 1


class Node:
    def __init__(self, src_i, dst_i):
        self.src_i = src_i
        self.dst_i = dst_i
        self.prev = None  # 前一个节点
        self.operate = PASS  # node 由什么操作而来

    @property
    def k(self):
        """斜率"""
        return self.src_i - self.dst_i

    def __hash__(self):
        return self.k

    def __iter__(self):
        operate_list = []

        node = self
        while node.prev is not None:
            operate_list.append(node.operate)
            node = node.prev

        return reversed(operate_list)

    def __eq__(self, other):
        return self.src_i == other.src_i and self.dst_i == other.dst_i

    def __lt__(self, other):
        return self.src_i < other.src_i and self.dst_i < other.dst_i

    def __le__(self, other):
        return self.src_i <= other.src_i and self.dst_i <= other.dst_i

    def grow(self, operate) -> 'Node':
        """
        获取不同操作的下一节点
        :param operate:int
        :return: Node
        """
        if operate == DEL:
            new_node = Node(self.src_i + 1, self.dst_i)
        elif operate == PASS:
            new_node = Node(self.src_i + 1, self.dst_i + 1)
        elif operate == ADD:
            new_node = Node(self.src_i, self.dst_i + 1)
        else:
            raise Exception(f'unknown operate {operate}')

        new_node.prev = self
        new_node.operate = operate
        return new_node

    def __repr__(self):
        return f'({self.src_i}, {self.dst_i})'


class RecordList(list):
    def __init__(self, src_len: int, dst_len: int):
        super().__init__(repeat(None, dst_len + 1 + src_len))  # [-dst_len, src_len]
        self.dst_len = dst_len
        self.src_len = src_len

    def layer_iter(self, deep):
        left = -min(deep, self.dst_len)
        left += (left ^ deep) & 0b1

        right = min(deep, self.src_len)
        right -= (right ^ deep) & 0b1

        for i in range(left, right + 1, 2):  # +1 取闭区间
            node = self[i]
            if node is not None:
                yield node

    def push(self, node):
        if node.src_i <= self.src_len and node.dst_i <= self.dst_len:
            record = self[node.k]  # 相同斜率下的节点
            if not record:
                self[node.k] = node
            elif node.src_i > record.src_i:  # node 节点走得更远
                self[node.k] = node  # 覆盖更新
            elif node.src_i < record.src_i:
                return
            elif node.operate > record.operate:  # node 和 record 位置相同 (src_i相同, k相同=>dst_i相同)
                self[node.k] = node  # 覆盖更新, (先减后)加优于(先加后)减

    def __repr__(self):
        string = ','.join(map(lambda each: ' ' * 6 if each is None else str(each), self))
        return f'(-{self.dst_len}, {self.src_len}){string}'


def myers(src, dst) -> Node:
    end_node = Node(len(src), len(dst))

    node_list = RecordList(len(src), len(dst))
    node_list.push(Node(0, 0))

    for deep in range(len(node_list)):
        for node in node_list.layer_iter(deep):
            # print(node_list)
            if node == end_node:
                return node

            while node < end_node and src[node.src_i] == dst[node.dst_i]:
                node = node.grow(PASS)

            node_list.push(node.grow(DEL))
            node_list.push(node.grow(ADD))

    raise Exception('myers arithmetic unexpected terminal')


def diff(src, dst) -> iter:
    prev_operate = None
    seg = []

    src_i, dst_i = 0, 0
    for operate in myers(src, dst):
        if (operate != prev_operate) and (prev_operate is not None):
            yield prev_operate, ''.join(seg)
            seg.clear()

        prev_operate = operate
        if operate == DEL:
            seg.append(src[src_i])
            src_i += 1
        elif operate == PASS:
            assert src[src_i] == dst[dst_i]
            seg.append(src[src_i])
            src_i += 1
            dst_i += 1
        elif operate == ADD:
            seg.append(dst[dst_i])
            dst_i += 1

    yield prev_operate, ''.join(seg)


if __name__ == '__main__' and 1:
    src = 'ABCABBA'
    dst = 'CBABAC'

    for operate, seg in diff(src, dst):
        print(operate, seg)
