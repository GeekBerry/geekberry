import re
import sys
from geekberry.collections import named_tuple

__all__ = ['sym', 'SymbolBase', 'SymbolTable', 'StreamBase', 'Stream', 'RDStream']

# TODO 倒置 Stream 和 Symbol 关系 ???

# from itertools import count  # DEBUG
# line = count(0)  # DEBUG

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
    Position = named_tuple('index', 'symbol')

    class Record(named_tuple('index', 'parsed')):
        def __new__(cls, index=-1, parsed=None):
            return super().__new__(cls, index, parsed)

        def __le__(self, other):
            return self.index <= other.index

        def empty(self):
            return self.index == -1 and self.parsed is None

    def __init__(self, string, begin=0, end=None):
        super().__init__(string, begin, end)
        self.stack = []  # [symbol, ...]
        self.recursive_stack = []  # [symbol, ...]
        self.record = {}  # {(symbol, start_pos):Record, ...}

    def parse(self, symbol):
        # print(f'{next(line):04d}{len(self.stack):4} {" "*4*len(self.stack)}START '
        #       f'{symbol} << "{self.behind(40)}"')
        pos = self.Position(self.index, symbol)

        record = self.record.get(pos)
        if record is None:
            self.stack.append(symbol)
            record = self.recursive_parser(symbol)
            self.stack.pop(-1)
        elif record.empty():  # 有记录且 record 为空, 说明 symbol 被递归访问
            self.recursive_stack.append(symbol)  # 本符号算失败
        else:
            self.index = record.index  # 移动索引至纪录位置

        # print(f'{next(line):04d}{len(self.stack):4} {" "*4*len(self.stack)}END '
        #       f'{symbol} = "{repr(record.parsed)}" << "{self.behind(40)}"')
        return record.parsed

    def recursive_parser(self, symbol):
        pos = self.Position(self.index, symbol)

        record = RDStream.Record()
        while True:
            self.index = pos.index  # 复位再解析
            self.record[pos] = record  # 更新记录

            parsed = super().parse(pos.symbol)  # 递归
            record = self.Record(self.index, parsed)

            if not self.recursive_stack:  # 解析中，没有左递归符号
                self.record[pos] = record
            elif self.recursive_stack[-1] != pos.symbol:  # symbol 非当前递归符号
                del self.record[pos]  # 清除访问记录
            elif record <= self.record[pos]:  # 解析没有前进,
                record = self.record[pos]  # 留下最长匹配的结果
                self.recursive_stack.pop(-1)
            else:
                continue  # 再次解析
            break
        return record

    def reset(self):
        super().reset()
        self.record = {}
        self.recursive_stack = []


# =============================================================================
class SymbolBase:
    name = ''  # 显示用名字

    def __or__(self, other) -> 'AnySymbol':
        return AnySymbol([self, sym(other)])

    def __mul__(self, arg) -> 'RepeatSymbol':
        """
        :param arg: int|tuple(int, int)
        :return: RepeatSymbol

        >>> sym()*3
        >>> sym()*(0, 5)
        >>> sym()*(0, ...)
        """
        try:
            begin, end = arg
        except TypeError:
            begin, end = arg, arg
        return RepeatSymbol(self, begin, end)

    @NotImplementedError
    def match(self, stream: StreamBase):
        """
        :param stream: SymbolBase
        :return: str or None
        """
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
        return repr(self.string)


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

    def __or__(self, other) -> 'AnySymbol':
        return AnySymbol(self.symbols + [other])

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
