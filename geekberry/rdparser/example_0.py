from geekberry.rdparser.rdparser import *


class T(SymbolTable):
    def __init__(self):
        super().__init__()
        # 终结符
        ends = sym(re.compile('\s*'), name='ends')
        integer = sym(re.compile(r'[0-9]+'), func=int, name='integer')
        # 非终结符
        self['Start'] = ends, self['Expr'], ends
        self['Expr'] = self['Term'], sym(ends, ['+', '-'], ends, self['Term']) * (0, ...)
        self['Term'] = self['Fact'], sym(ends, ['*', '/'], ends, self['Fact']) * (0, ...)
        self['Fact'] = sym('(', ends, self['Expr'], ends, ')') | integer | Exception('except Fact')

    def Start(self, match):
        return match[1]  # Start -> Ends Var Ends

    def Expr(self, match):
        var, vars = match
        for each in vars:  # [ends, + or -, ends, Fact]
            if each[1] == '+':
                var += each[3]
            elif each[1] == '-':
                var -= each[3]
        return var

    def Term(self, match):
        var, vars = match
        for each in vars:  # [ends, * or /, ends, Fact]
            if each[1] == '*':
                var *= each[3]
            elif each[1] == '/':
                var /= each[3]
        return var

    def Fact(self, match):
        if type(match) is list:  # Var -> ( Ends AddSub Ends )
            return match[2]
        else:  # Var -> Int
            return match


if __name__ == '__main__':
    s = Stream(" 12345 + ")
    t = T()
    print(t.dump())
    try:
        p = s.parse(t['Start'])
    except Exception as e:
        sys.stderr.write(f'{e}\n')
        # 12345 +
        #         ^except Fact
    else:
        print(p)
