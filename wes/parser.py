"""
ACKNOWLEDGEMENTS:

Many of these parsing routines were inspired by (or taken from) Guido van
Rossum's article series on PEG parsing:

https://medium.com/@gvanrossum_83706/peg-parsing-series-de5d41b2ed60
"""
from __future__ import annotations

import contextlib
import functools
import re
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    Optional,
    TextIO,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from wes.exceptions import Reset, Stop
from wes.lexer import Eof, Lexer, Newline, Text, TokenStream
from wes.utils import serialize_dict, str_to_int

NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
VAL_RE = re.compile(r"^(0b[01_]+|0o[0-7_]+|[0-9_]+|0x[a-fA-F0-9_]+)$")

T = TypeVar("T")


class Node:
    __slots__ = ("toks",)

    toks: Tuple[Text, ...]

    def __init__(self, *, toks: Optional[Tuple[Text, ...]] = None):
        if toks is None:
            toks = ()

        self.toks = toks

    @property
    def slot_values(self) -> Tuple[Any, ...]:
        return tuple(getattr(self, s) for s in self.__slots__ if s != "toks")

    def __repr__(self) -> str:  # pragma: no cover
        elems_repr = ", ".join(repr(i) for i in self.slot_values)
        cls_name = self.__class__.__qualname__

        return f"{cls_name}({elems_repr})"

    def __eq__(self, other: Any) -> bool:
        if type(self) is not type(other):
            return False

        # fail early if we find a mismatch
        for x, y in zip(self.slot_values, other.slot_values):
            if x != y:
                return False

        return True


class File(Node):
    __slots__ = ("stmts",)

    stmts: Tuple[Union[Stmt, Expr], ...]

    def __init__(self, stmts: Tuple[Union[Stmt, Expr], ...]):
        self.stmts = stmts

        # we have all the tokens in the statement nodes
        super().__init__(toks=tuple())


class Stmt(Node):
    __slots__ = tuple()


class Label(Stmt):
    __slots__ = ("name",)

    name: str

    def __init__(self, name: str, **kwargs: Any):
        self.name = name

        super().__init__(**kwargs)


class Offset(Stmt):
    __slots__ = ("offset", "relative")

    offset: int
    relative: Optional[str]

    def __init__(self, offset: int, relative: Optional[str], **kwargs: Any):
        self.offset = offset
        self.relative = relative

        super().__init__(**kwargs)


class Op(Stmt):
    __slots__ = ("mnemonic", "args")

    mnemonic: str
    args: Tuple[Union[str, int], ...]

    def __init__(self, mnemonic: str, args: Tuple[Union[str, int], ...], **kwargs: Any):
        self.mnemonic = mnemonic
        self.args = args

        super().__init__(**kwargs)


class Expr(Node):
    __slots__ = tuple()


class Name(Expr):
    __slots__ = ("name",)

    name: str

    def __init__(self, name: str, **kwargs: Any):
        self.name = name

        super().__init__(**kwargs)


class Val(Expr):
    __slots__ = ("val",)

    val: int

    def __init__(self, val: int, **kwargs: Any):
        self.val = val

        super().__init__(**kwargs)


class UnExpr(Expr):
    __slots__ = ("op", "x")

    op: str
    x: Expr

    def __init__(self, op: str, x: Expr, **kwargs: Any):
        self.op = op
        self.x = x

        super().__init__(**kwargs)


class BinExpr(Expr):
    __slots__ = ("x", "op", "y")

    x: Expr
    op: str
    y: Expr

    def __init__(self, x: Expr, op: str, y: Expr, **kwargs: Any):
        self.x = x
        self.op = op
        self.y = y

        super().__init__(**kwargs)


def optional(method: Callable[[Parser], T]) -> Callable[[Parser], Optional[T]]:
    @functools.wraps(method)
    def new_method(self) -> Optional[T]:
        res = None
        with self.reset():
            res = method(self)

        return res

    return new_method


U = TypeVar("U", bound=Node)


def cache(
    method: Callable[..., Optional[U]]
) -> Callable[..., Optional[U]]:  # pragma: no cover
    @functools.wraps(method)
    def new_method(self: Parser, *args: Any, **kwargs: Any) -> Optional[U]:
        key = (self.toks.mark(), method, args, serialize_dict(kwargs))

        if key in self.cache:
            res, end = self.cache[key]
            self.toks.reset(end)
        else:
            res = method(self, *args, **kwargs)
            end = self.toks.mark()
            self.cache[key] = res, end

        return cast(Optional[U], res)

    return new_method


def cache_left_rec(method: Callable[..., Optional[U]]) -> Callable[..., Optional[U]]:
    @functools.wraps(method)
    def new_method(self: Parser, *args: Any, **kwargs: Any) -> Optional[U]:
        pos = self.toks.mark()
        key = (pos, method, args, serialize_dict(kwargs))

        if key in self.cache:
            res, end = self.cache[key]
            self.toks.reset(end)
        else:
            # prime cache with failure result
            last_res, last_pos = None, pos
            self.cache[key] = last_res, last_pos

            # loop until no longer parse result is obtained
            while True:
                self.toks.reset(pos)
                res = method(self, *args, **kwargs)

                end = self.toks.mark()
                if end <= last_pos:
                    break

                last_res, last_pos = res, end
                self.cache[key] = last_res, last_pos

            res = last_res
            self.toks.reset(last_pos)

        return cast(Optional[U], res)

    return new_method


Pos = int
ParserMethod = Callable[..., Any]
Args = Tuple[Any, ...]
Kwargs = Tuple[Tuple[str, Any], ...]

CacheKey = Tuple[Pos, ParserMethod, Args, Kwargs]
CacheValue = Tuple[Optional[Node], Pos]


class Parser:
    __slots__ = ("toks", "cache", "last_reset")

    toks: TokenStream
    cache: Dict[CacheKey, CacheValue]
    last_reset: Optional[Reset]

    def __init__(self, lexer: Lexer):
        self.toks = TokenStream(lexer)
        self.cache = {}
        self.last_reset = None

    @classmethod
    def from_str(cls, text: str) -> Parser:
        lexer = Lexer.from_str(text)
        return cls(lexer)

    @classmethod
    def from_buf(cls, buf: TextIO) -> Parser:
        lexer = Lexer(buf)
        return cls(lexer)

    @contextlib.contextmanager
    def reset(self) -> Iterator[None]:
        pos = self.toks.mark()
        try:
            yield
        except Reset as e:
            self.last_reset = e
            self.toks.reset(pos)

    def expect(self, *alts: str, error: Type[Exception] = Reset) -> Text:
        tok = self.toks.get()

        if not isinstance(tok, Text):
            raise error("unexpected end of line", (tok,))
        if len(alts) > 0 and tok.text not in alts:
            if len(alts) == 1:
                raise error(f"expected '{alts[0]}'", (tok,))
            else:
                raise error(f"expected one of {repr(alts)}", (tok,))

        return tok

    def expect_newline(self, error: Type[Exception] = Reset) -> Newline:
        tok = self.toks.get()

        if not isinstance(tok, Newline):
            raise error("expected end of line", (tok,))

        return tok

    def maybe(self, *alts: str) -> Optional[Text]:
        res = None
        with self.reset():
            res = self.expect(*alts)

        return res

    def parse_file(self) -> File:
        stmts = []
        while stmt := self.parse_stmt():
            stmts.append(stmt)

        tok = self.toks.get()
        if not isinstance(tok, Eof):
            if self.last_reset is None:  # pragma: no cover
                raise Exception("invariant")

            raise Stop(self.last_reset.msg, self.last_reset.toks) from self.last_reset

        return File(tuple(stmts))

    def parse_stmt(self) -> Optional[Union[Stmt, Expr]]:
        if offset := self.parse_offset():
            return offset
        elif label := self.parse_label():
            return label
        return self.parse_inst()

    def parse_offset(self) -> Optional[Offset]:
        if off := self.parse_relative():
            return off
        else:
            return self.parse_absolute()

    @optional
    def parse_relative(self) -> Offset:
        relative = self.expect("+", "-")
        val = self.expect()
        colon = self.expect(":")

        if not VAL_RE.match(val.text):
            raise Reset(f"{repr(val.text)} is not valid offset", (val,))

        # optional trailing newline
        with self.reset():
            self.expect_newline()

        return Offset(str_to_int(val.text), relative.text, toks=(relative, val, colon))

    @optional
    def parse_absolute(self) -> Offset:
        val = self.expect()
        colon = self.expect(":")

        if not VAL_RE.match(val.text):
            raise Reset(f"{repr(val.text)} is not valid offset", (val,))

        # optional trailing newline
        with self.reset():
            self.expect_newline()

        return Offset(str_to_int(val.text), None, toks=(val, colon))

    @optional
    def parse_label(self) -> Label:
        name = self.expect()
        colon = self.expect(":")

        if not NAME_RE.match(name.text):
            raise Reset(f"{repr(name.text)} is not valid name", (name,))

        # optional trailing newline
        with self.reset():
            self.expect_newline()

        return Label(name.text, toks=(name, colon))

    def parse_inst(self) -> Union[Op, Expr, None]:
        if nullary := self.parse_nullary():
            return nullary
        elif unary := self.parse_unary():
            return unary
        return self.parse_binary()

    @optional
    def parse_nullary(self) -> Optional[Expr]:
        expr = self.parse_expr()
        self.expect_newline()

        return expr

    @optional
    def parse_unary(self) -> Op:
        mnemonic = self.expect()
        if not NAME_RE.match(mnemonic.text):
            raise Reset(f"{repr(mnemonic.text)} is not a valid name", (mnemonic,))

        arg = self.expect()
        self.expect_newline()

        arg_ = self.parse_arg_token(arg)

        return Op(mnemonic.text, (arg_,), toks=(mnemonic, arg))

    @optional
    def parse_binary(self) -> Op:
        mnemonic = self.expect()
        if not NAME_RE.match(mnemonic.text):
            raise Reset(
                f"{repr(mnemonic.text)} is not a valid name or expression", (mnemonic,)
            )

        arg1 = self.expect()
        comma = self.expect(",", error=Stop)
        arg2 = self.expect(error=Stop)
        self.expect_newline(error=Stop)

        arg1_ = self.parse_arg_token(arg1)
        arg2_ = self.parse_arg_token(arg2)

        return Op(mnemonic.text, (arg1_, arg2_), toks=(mnemonic, arg1, comma, arg2))

    def parse_arg_token(self, name_or_val: Text) -> Union[str, int]:
        if VAL_RE.match(name_or_val.text):
            return str_to_int(name_or_val.text)
        elif NAME_RE.match(name_or_val.text):
            return name_or_val.text
        else:
            raise Stop(
                f"{repr(name_or_val.text)} is not a valid name or expression",
                (name_or_val,),
            )

    @optional
    def parse_atom(self) -> Expr:
        if l_paren := self.maybe("("):
            expr = self.parse_expr()
            if expr is None:
                raise Stop(f"expected expression after '{l_paren.text}'", (l_paren,))
            r_paren = self.expect(")")

            new_toks = (l_paren,) + expr.toks + (r_paren,)
            return type(expr)(*expr.slot_values, toks=new_toks)

        else:
            name_or_val = self.expect()

            if VAL_RE.match(name_or_val.text):
                return Val(str_to_int(name_or_val.text), toks=(name_or_val,))
            elif NAME_RE.match(name_or_val.text):
                return Name(name_or_val.text, toks=(name_or_val,))
            else:
                raise Reset(
                    f"{repr(name_or_val.text)} is not a valid name or integer",
                    (name_or_val,),
                )

    def parse_power(self: Parser) -> Optional[Expr]:
        x = self.parse_atom()
        if x is None:
            return None

        if op := self.maybe("**"):
            y = self.parse_factor()
            if y is None:
                raise Stop(f"expected expression after '{op.text}' operator", (op,))

            return BinExpr(x, op.text, y, toks=x.toks + (op,) + y.toks)
        else:
            return x

    @cache_left_rec
    def parse_factor(self: Parser) -> Optional[Expr]:
        if op := self.maybe("-", "~"):
            x = self.parse_factor()
            if x is None:
                raise Stop(f"expected expression after '{op.text}' operator", (op,))

            return UnExpr(op.text, x, toks=(op,) + x.toks)

        return self.parse_power()

    @staticmethod
    def make_expr_parser(
        name: str,
        ops: Tuple[str, ...],
        rhs: Callable[[Parser], Optional[Expr]],
    ) -> Callable[[Parser], Optional[Expr]]:
        def parser(self: Parser) -> Optional[Expr]:
            with self.reset():
                if x := parser_(self):
                    op = self.expect(*ops)

                    y = rhs(self)
                    if y is None:
                        raise Stop(
                            f"expected expression after '{op.text}' operator", (op,)
                        )

                    return BinExpr(x, op.text, y, toks=x.toks + (op,) + y.toks)

            return rhs(self)

        parser.__name__ = name

        parser_ = cache_left_rec(parser)

        return parser_

    parse_term = make_expr_parser("parse_term", ("*", "/", "%"), parse_factor)
    parse_sum = make_expr_parser("parse_sum", ("+", "-"), parse_term)
    parse_shift = make_expr_parser("parse_shift", ("<<", ">>"), parse_sum)
    parse_and = make_expr_parser("parse_and", ("&",), parse_shift)
    parse_xor = make_expr_parser("parse_xor", ("^",), parse_and)
    parse_expr = make_expr_parser("parse_expr", ("|",), parse_xor)
