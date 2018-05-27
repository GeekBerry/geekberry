import re, sys

REGULAR_TYPE = type(re.compile(''))


class StreamBase:
    index = None

    def __init__(self, string, begin=0, end=None):
        self.string = string
        self.begin = begin
        self.end = end if (end is not None) else len(string) + begin
        self.reset()

    def __iter__(self):
        return self

    def __next__(self):
        if self.index < self.end:
            char = self.string[self.index]
            self.index += 1
            return char
        else:
            raise StopIteration

    def eof(self) -> bool:
        return self.index >= self.end

    # -------------------------------------------------------------------------
    def reset(self):
        self.index = self.begin

    def parse(self, symbol):
        start_pos = self.index

        matched = symbol.match(self)
        if matched is None:  # matched 为 None 不进行制导翻译
            self.index = start_pos  # 恢复现场
            return None
        else:
            return symbol.func(matched)

    def front(self, count):
        return self.string[self.index - count:self.index]

    def behind(self, count):
        return self.string[self.index:self.index + count]


class Stream(StreamBase):
    stack = None

    def reset(self):
        super().reset()
        self.stack = []

    def parse(self, symbol):
        self.stack.append(symbol)
        parsed = super().parse(symbol)
        self.stack.pop(-1)
        return parsed


class RDStream(StreamBase):
    def __init__(self, string, begin=0, end=None):
        super().__init__(string, begin, end)
        self.stack = []  # [symbol, ...]
        self.record = {}  # {(symbol, start_pos):(parsed, end_pos), ...}
        self.recursive_symbol = None

    def parse(self, symbol):
        print(f"{' '*4*len(self.stack)}{symbol}{'{'}behind='{self.behind(40)}'")
        start_pos = self.index

        if (symbol, self.index) not in self.record:  # 没有记录, symbol 肯定不是递归符号
            self.stack.append(symbol)

            self.record[symbol, start_pos] = None, -1
            while True:
                parsed = super().parse(symbol)

                if self.recursive_symbol is None:  # 解析中，没有左递归符号，记录并返回
                    self.record[symbol, start_pos] = parsed, self.index
                    break

                if self.recursive_symbol != symbol:  # 有左递归，当前符号非递归符号 => 左递归符号在栈下方
                    del self.record[symbol, start_pos]  # 清除访问记录
                    break

                # 在最后一次左递归满足后，肯可能再次生成短解析结果，需要进行最长匹配检查
                r_parsed, r_end_pos = self.record[symbol, start_pos]
                if self.index <= r_end_pos:  # 解析没有前进
                    parsed, self.index = r_parsed, r_end_pos  # 留下最长匹配的结果
                    self.recursive_symbol = None  # 递归解析结束, 清除递归记录
                    break

                self.record[symbol, start_pos] = parsed, self.index
                self.index = start_pos  # 复原位置才能再次进行解析

            self.stack.pop(-1)
        else:
            parsed, end_pos = self.record[symbol, start_pos]
            if end_pos == -1:  # 有记录 且 end_pos 为负数, 说明symbol被递归访问
                # assert parsed is None
                # assert self.index == start_pos
                self.recursive_symbol = symbol
            else:
                self.index = end_pos

        print(f"{' '*4*len(self.stack)}{'}'}parsed='{repr(parsed)}', behind='{self.behind(40)}'\n")

        return parsed

    def reset(self):
        super().reset()
        self.record = {}


# =============================================================================
class SymbolBase:
    name = ''  # 显示用名字

    def __or__(self, other):
        symbol = sym(other)

        if isinstance(self, AnySymbol):
            return AnySymbol(self.symbols + [symbol])
        else:
            return AnySymbol([self, symbol])

    def __mul__(self, arg):
        if type(arg) is int:
            return RepeatSymbol(self, arg, arg)
        else:
            return RepeatSymbol(self, arg[0], arg[1])

    @NotImplementedError
    def match(self, stream):
        pass

    def func(self, matched):
        return matched

    def __str__(self):
        if self.name:
            return self.name
        else:
            return self.dump()

    def __repr__(self):  # XXX
        return f'{self}<{hash(self)}>'

    @NotImplementedError
    def dump(self):
        pass


class TerminalSymbol(SymbolBase):
    pass


class EmptySymbol(TerminalSymbol):
    def match(self, stream):
        return ''

    def dump(self):
        return ''


class StringSymbol(TerminalSymbol):
    def __init__(self, string):
        self.string = string

    def match(self, stream):
        if stream.string.startswith(self.string, stream.index):
            stream.index += len(self.string)
            return self.string
        else:
            return None

    def dump(self):
        return f"'{self.string}'"


class RegularSymbol(TerminalSymbol):
    def __init__(self, regular):
        assert isinstance(regular, REGULAR_TYPE)
        self.regular = regular

    def match(self, stream):
        result = self.regular.match(stream.string, stream.index, stream.end)
        if result is not None:
            result = result.group()
            stream.index += len(result)
        return result

    def dump(self):
        return f"re'{ str(self.regular)[12:-2] }'"  # [12:-2] 提取正则字符串部分


class ExceptionSymbol(TerminalSymbol):
    def __init__(self, exception):
        self.exception = exception

    def match(self, stream):
        expect_str = list()
        expect_str.append('\nParserStack(Name: Symbol)\n')
        for i, symbol in enumerate(stream.stack):
            expect_str.append(f'{"    "*i}{symbol.name}: {symbol.dump()}\n')

        # 40: 半个dos屏幕宽度
        front = stream.front(40).replace('\n', r'\n')
        behind = stream.behind(40).replace('\n', r'\n')
        expect_str.append(f'{front}{behind}\n')
        expect_str.append(f"{' '*len(front)}^{self.exception}\n")

        sys.stderr.write(''.join(expect_str))
        raise self.exception

    def dump(self):
        return f'{self.exception.__class__.__name__}({"".join(map(repr, self.exception.args))})'


# -----------------------------------------------------------------------------
class NonTerminalSymbol(SymbolBase):
    pass


class AllSymbol(NonTerminalSymbol):
    def __init__(self, symbols):
        self.symbols = symbols

    def match(self, stream):
        results = []
        for symbol in self.symbols:
            result = stream.parse(symbol)
            if result is not None:
                results.append(result)
            else:
                return None
        return results

    def dump(self):
        return f"({','.join( map(str, self.symbols) )})"


class AnySymbol(NonTerminalSymbol):
    def __init__(self, symbols):
        self.symbols = symbols

    def match(self, stream):
        for symbol in self.symbols:
            result = stream.parse(symbol)
            if result is not None:
                return result
        return None

    def dump(self):
        return f'[{ "|".join( map(str, self.symbols) ) }]'


class RepeatSymbol(NonTerminalSymbol):
    def __init__(self, symbol, least: int, most):
        assert isinstance(symbol, SymbolBase)
        assert type(least) == int
        assert type(most) == int or (most is ...)

        self.symbol = symbol
        self.least = least
        self.most = most

    def match(self, stream):
        results = []
        # 无长度限制 或 results 长度不足
        while (self.most is ...) or (len(results) < self.most):
            result = stream.parse(self.symbol)
            if result is not None:
                results.append(result)
            else:
                break

        return results if len(results) >= self.least else None

    def dump(self):
        most = "..." if self.most is ... else self.most
        return f'{self.symbol}*({self.least},{most})'


class KeySymbol(NonTerminalSymbol):
    def __init__(self, table, key):
        self.table = table
        self.key = key

    @property
    def symbol(self):
        return self.table.get(self.key)

    def match(self, stream):
        return self.symbol.match(stream)

    def __hash__(self):
        return self.symbol.__hash__()

    def __eq__(self, other):
        return self.symbol.__eq__(other)

    def dump(self):
        return f'{self.key}'


# -----------------------------------------------------------------------------
class SymbolTable(dict):
    def __setitem__(self, key, value):
        super().__setitem__(key, sym(value))

    def __getitem__(self, item: str):
        symbol = KeySymbol(self, item)
        if hasattr(self, item):
            symbol.func = getattr(self, item)
        return symbol

    def dump(self):
        dump_str = []
        for key, value in self.items():
            dump_str.append(f'{key}->{value.dump()}')
        return '\n'.join(dump_str)


# ==========================================================================================
def sym(*args, func=None, name=None):
    # 生成 arg
    if len(args) > 1:
        arg = args  # type(arg) is tuple
    elif len(args) < 0:
        arg = None
    else:
        arg = args[0]

    # 依据 arg 生成 symbol
    if type(arg) is str:
        symbol = StringSymbol(arg)
    elif arg is None:
        symbol = EmptySymbol()
    elif type(arg) is REGULAR_TYPE:
        symbol = RegularSymbol(arg)
    elif type(arg) is tuple:
        symbol = AllSymbol(list(map(sym, arg)))
    elif type(arg) is list:
        symbol = AnySymbol(list(map(sym, arg)))
    elif isinstance(arg, SymbolBase):
        symbol = arg  # XXX 研究是否需要进行拷贝
    elif isinstance(arg, Exception):
        symbol = ExceptionSymbol(arg)
    else:
        raise TypeError(f'未知类型 {type(arg)}')

    if func is not None:
        symbol.func = func

    if name is not None:
        symbol.name = name

    return symbol
