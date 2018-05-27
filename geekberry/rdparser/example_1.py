from geekberry.rdparser.rdparser import *


class T(SymbolTable):
    def __init__(self):
        self['A'] = sym(self['A'], ',' 'a') | 'a'


if __name__ == '__main__':
    s = RDStream("a,a,a")
    t = T()
    print(t.dump())
    p = s.parse(t['A'])
    print(p)
