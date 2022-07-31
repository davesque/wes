from __future__ import annotations

import contextlib
import re
from typing import (
    Any,
    Callable,
    Iterator,
    Optional,
    TextIO,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from wes.exceptions import EndOfTokens, Reset, Stop
from wes.lexer import Eof, Lexer, Newline, Text, Token, TokenStream
from wes.utils import str_to_int

NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
VAL_RE = re.compile(r"^(0b[01_]+|0o[0-7_]+|[0-9_]+|0x[a-fA-F0-9_]+)$")

T = TypeVar("T")


class Node:
    __slots__ = ("toks",)

    toks: Tuple[Text, ...]  # type: ignore

    def __init__(self, toks: Tuple[Text, ...]):
        self.toks = toks

    @property
    def _slot_values(self) -> Tuple[Any, ...]:
        return tuple(getattr(self, s) for s in self.__slots__ if s != "toks")

    def __repr__(self) -> str:  # pragma: no cover
        elems_repr = ", ".join(repr(i) for i in self._slot_values)
        cls_name = self.__class__.__qualname__

        return f"{cls_name}({elems_repr})"

    def __eq__(self, other: Any) -> bool:
        types_match = type(self) is type(other)
        # a bit faster to check the negative condition here to avoid doing the
        # comparison for all values if we encounter one mismatch
        slots_mismatch = any(
            x != y for x, y in zip(self._slot_values, other._slot_values)
        )

        return types_match and not slots_mismatch


class File(Node):
    __slots__ = ("stmts",)

    stmts: Tuple[Stmt, ...]

    def __init__(self, stmts: Tuple[Stmt, ...]):
        self.stmts = stmts

        # we have all the tokens in the statement nodes
        super().__init__(tuple())


class Stmt(Node):
    __slots__ = tuple()


class Label(Stmt):
    __slots__ = ("name",)

    name: str

    def __init__(self, name: str, toks: Tuple[Text, ...]):
        self.name = name

        super().__init__(toks)


class Offset(Stmt):
    __slots__ = ("offset", "relative")

    offset: int
    relative: Optional[str]

    def __init__(self, offset: int, relative: Optional[str], toks: Tuple[Text, ...]):
        self.offset = offset
        self.relative = relative

        super().__init__(toks)


class Op(Stmt):
    __slots__ = ("mnemonic", "args")

    mnemonic: str
    args: Tuple[Union[str, int], ...]

    def __init__(
        self, mnemonic: str, args: Tuple[Union[str, int], ...], toks: Tuple[Text, ...]
    ):
        self.mnemonic = mnemonic
        self.args = args

        super().__init__(toks)


class Val(Stmt):
    __slots__ = ("val",)

    val: int

    def __init__(self, val: int, toks: Tuple[Text, ...]):
        self.val = val

        super().__init__(toks)


def optional(old_method: Callable[[Parser], T]) -> Callable[[Parser], Optional[T]]:
    def new_method(self) -> Optional[T]:
        res = None
        with self.reset():
            res = old_method(self)

        return res

    return new_method


class Parser:
    __slots__ = ("toks",)

    toks: TokenStream

    def __init__(self, lexer: Lexer):
        self.toks = TokenStream(lexer)

    @classmethod
    def from_str(cls, text: str) -> Parser:
        lexer = Lexer.from_str(text)
        return cls(lexer)

    @classmethod
    def from_buf(cls, buf: TextIO) -> Parser:
        lexer = Lexer(buf)
        return cls(lexer)

    def get(self, error: Type[Exception] = Reset) -> Token:
        try:
            return self.toks.get()
        except EndOfTokens:
            raise error("unexpected end of tokens", ())

    @contextlib.contextmanager
    def reset(self) -> Iterator[None]:
        pos = self.toks.mark()
        try:
            yield
        except Reset:
            self.toks.reset(pos)

    def expect(
        self, *alts: str, error: Type[Exception] = Reset
    ) -> Text:
        tok = self.get()

        if not isinstance(tok, Text):
            raise error("unexpected end of line", (tok,))
        if len(alts) > 0 and tok.text not in alts:
            if len(alts) == 1:
                raise error(f"expected '{alts[0]}'", (tok,))
            else:
                raise error(f"expected one of {repr(alts)}", (tok,))

        return tok

    def expect_newline(self, error: Type[Exception] = Reset) -> Newline:
        tok = self.get()

        if not isinstance(tok, Newline):
            raise error("expected end of line", (tok,))

        return tok

    def parse_file(self) -> File:
        stmts = []
        while stmt := self.parse_stmt():
            stmts.append(stmt)

        self.parse_eof()

        return File(tuple(stmts))

    def parse_stmt(self) -> Optional[Stmt]:
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

        return Offset(str_to_int(val.text), relative.text, (relative, val, colon))

    @optional
    def parse_absolute(self) -> Offset:
        val = self.expect()
        colon = self.expect(":")

        if not VAL_RE.match(val.text):
            raise Reset(f"{repr(val.text)} is not valid offset", (val,))

        # optional trailing newline
        with self.reset():
            self.expect_newline()

        return Offset(str_to_int(val.text), None, (val, colon))

    @optional
    def parse_label(self) -> Label:
        name = self.expect()
        colon = self.expect(":")

        if not NAME_RE.match(name.text):
            raise Reset(f"{repr(name.text)} is not valid name", (name,))

        # optional trailing newline
        with self.reset():
            self.expect_newline()

        return Label(name.text, (name, colon))

    def parse_inst(self) -> Union[Op, Val, None]:
        if nullary := self.parse_nullary():
            return nullary
        elif unary := self.parse_unary():
            return unary
        return self.parse_binary()

    @optional
    def parse_nullary(self) -> Union[Op, Val]:
        name_or_val = self.expect()
        _ = self.expect_newline()

        if NAME_RE.match(name_or_val.text):
            return Op(name_or_val.text, (), (name_or_val,))
        elif VAL_RE.match(name_or_val.text):
            return Val(str_to_int(name_or_val.text), (name_or_val,))
        else:
            raise Stop(
                f"{repr(name_or_val.text)} is not a valid name or integer",
                (name_or_val,),
            )

    @optional
    def parse_unary(self) -> Op:
        mnemonic = self.expect()
        arg = self.expect()
        _ = self.expect_newline()

        if not NAME_RE.match(mnemonic.text):
            raise Stop(f"{repr(mnemonic.text)} is not a valid name", (mnemonic,))

        arg_ = self.parse_arg_token(arg)

        return Op(mnemonic.text, (arg_,), (mnemonic, arg))

    @optional
    def parse_binary(self) -> Op:
        mnemonic = self.expect()
        arg1 = self.expect()
        comma = self.expect(",", error=Stop)
        arg2 = self.expect(error=Stop)
        _ = self.expect_newline(error=Stop)

        if not NAME_RE.match(mnemonic.text):
            raise Stop(f"{repr(mnemonic.text)} is not a valid name", (mnemonic,))

        arg1_ = self.parse_arg_token(arg1)
        arg2_ = self.parse_arg_token(arg2)

        return Op(mnemonic.text, (arg1_, arg2_), (mnemonic, arg1, comma, arg2))

    def parse_arg_token(self, name_or_val: Text) -> Union[str, int]:
        if VAL_RE.match(name_or_val.text):
            return str_to_int(name_or_val.text)
        elif NAME_RE.match(name_or_val.text):
            return name_or_val.text
        else:
            raise Stop(
                f"{repr(name_or_val.text)} is not a valid name or integer",
                (name_or_val,),
            )

    def parse_eof(self) -> None:
        tok = self.get()
        if not isinstance(tok, Eof):  # pragma: no cover
            raise Stop("expected end of file", (tok,))
