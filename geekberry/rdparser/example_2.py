import re
from geekberry.rdparser import *


class ArithmeticTable(SymbolTable):
    def __init__(self):
        ends = sym(re.compile('\s*'), name='ends')
        integer = sym(re.compile(r'[0-9]+'), func=int, name='integer')

        self['S'] = ends, self['E'], ends
        self['E'] = sym(self['E'], ends, ['+', '-'], ends, self['T']) | self['T']
        self['T'] = sym(self['T'], ends, ['*', '/'], ends, self['F']) | self['F']
        self['F'] = sym('(', self['S'], ')') | integer

    def S(self, arg):
        return arg[1]  # S -> ends, E, ends

    def E(self, arg):
        if type(arg) is list:  # E -> E, ends, ['+', '-'], ends, T
            if arg[2] == '+':
                return arg[0] + arg[4]
            elif arg[2] == '-':
                return arg[0] - arg[4]
        else:  # E -> T
            return arg

    def T(self, arg):
        if type(arg) is list:  # T -> T, ends, ['*', '/'], ends, F
            if arg[2] == '*':
                return arg[0] * arg[4]
            elif arg[2] == '/':
                return arg[0] / arg[4]
        else:  # T -> F
            return arg

    def F(self, arg):
        if type(arg) is list:  # F -> '(', S, ')'
            return arg[1]
        else:  # F -> integer
            return arg


if __name__ == '__main__':
    stream = RDStream(" (1+5-4)*(2/(2-1)) ")
    table = ArithmeticTable()
    # print(table.dump())
    value = stream.parse(table['S'])
    print(value)
