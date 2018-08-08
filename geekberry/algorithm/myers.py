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
    operate = None

    @staticmethod
    def build(prev, operate=None):
        if operate == DEL:
            node = Node(prev.src_i + 1, prev.dst_i, prev)
        elif operate == PASS:
            node = Node(prev.src_i + 1, prev.dst_i + 1, prev)
        elif operate == ADD:
            node = Node(prev.src_i, prev.dst_i + 1, prev)
        else:
            node = Node(prev.src_i, prev.dst_i, prev)
        node.operate = operate
        return node

    def __init__(self, src_i, dst_i, prev=None):
        self.src_i = src_i
        self.dst_i = dst_i
        self.prev = prev

    @property
    def k(self):
        return self.src_i - self.dst_i

    def __hash__(self):
        return self.k

    def __iter__(self):
        reverse = []

        node = self
        while node.prev is not None:
            reverse.append(node.operate)
            node = node.prev

        return reversed(reverse)

    def __eq__(self, other):
        return self.src_i == other.src_i and self.dst_i == other.dst_i

    def __lt__(self, other):
        return self.src_i < other.src_i and self.dst_i < other.dst_i

    def __le__(self, other):
        return self.src_i <= other.src_i and self.dst_i <= other.dst_i

    def del_node(self):
        return Node.build(self, DEL)

    def add_node(self):
        return Node.build(self, ADD)

    def pass_node(self, old, new):
        end = Node(len(old), len(new))

        node = self
        while node < end and old[node.src_i] == new[node.dst_i]:
            node = Node.build(node, PASS)

        return node

    def __repr__(self):
        return f'({self.src_i}, {self.dst_i})'


class RecordList(list):
    def __init__(self, end_node: Node):
        super().__init__(repeat(None, end_node.src_i + end_node.dst_i + 1))
        self.end_node = end_node

    def layer_iter(self, deep):
        left = max(-deep, -self.end_node.dst_i)
        left += (left ^ deep) & 1

        right = min(deep, self.end_node.src_i)
        right -= (right ^ deep) & 1

        for i in range(left, right + 1, 2):  # +1 取闭区间
            node = self[i]
            if node is not None:
                yield node

    def push(self, node):
        if node <= self.end_node:
            record = self[node.k]
            if not record:
                self[node.k] = node
            elif node.src_i > record.src_i:
                self[node.k] = node
            elif node.src_i < record.src_i:
                return
            elif node.operate > record.operate:
                # 同一节点(src_i相同, k相同=>dst_i相同) 先减后加 优于 先加后减, operate 存放后操作
                self[node.k] = node

    def __repr__(self):
        string = ','.join(map(lambda each: ' ' * 6 if each is None else str(each), self))
        return f'(-{self.end_node.dst_i}, {self.end_node.src_i}){string}'


def myers(src, dst) -> Node:
    end_node = Node(len(src), len(dst))

    node_list = RecordList(end_node)
    node_list[0] = Node(0, 0)

    for deep in range(len(node_list)):
        for node in node_list.layer_iter(deep):
            if node == end_node:
                return node
            node = node.pass_node(src, dst)
            node_list.push(node.del_node())
            node_list.push(node.add_node())


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
            # assert src[src_i] == dst[dst_i]
            seg.append(src[src_i])
            src_i += 1
            dst_i += 1
        elif operate == ADD:
            seg.append(dst[dst_i])
            dst_i += 1

    yield prev_operate, ''.join(seg)


if __name__ == '__main__' and 1:
    import cProfile
    import pstats

    cprofile = cProfile.Profile()

    with open('2.txt', 'r', encoding='utf-8') as src_file, open('1.txt', 'r', encoding='utf-8') as dst_file:
        src = src_file.read()
        dst = dst_file.read()

        cprofile.run('list(diff(src, dst))')
        pstats.Stats(cprofile).strip_dirs().sort_stats('ncalls').sort_stats(-1).print_stats()

if __name__ == '__main__' and 1:
    src = 'ABCABBA'
    dst = 'CBABAC'

    for operate, seg in diff(src, dst):
        print(operate, seg)
