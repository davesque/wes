from __future__ import annotations

import re
from typing import Iterator, List, Optional, TextIO, Union

from .exceptions import EndOfTokens, RenderedError
from .lexer import Eof, Lexer, Newline, Text, Token
from .utils import str_to_int

NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
VAL_RE = re.compile(r"^(0b[01]+|0o[0-7]+|[0-9]+|0x[a-fA-F0-9]+)$")


class Node:
    __slots__ = ("toks",)

    toks: List[Text]  # type: ignore


class File(Node):
    __slots__ = ("stmts",)

    stmts: List[Stmt]

    def __init__(self, stmts: List[Stmt]):
        self.stmts = stmts

        self.toks = []
        for stmt in stmts:
            self.toks.extend(stmt.toks)

    def __repr__(self) -> str:  # pragma: no cover
        return f"File({repr(self.stmts)})"

    def __eq__(self, other) -> bool:
        return type(self) is type(other) and (self.stmts == other.stmts)


class Stmt(Node):
    __slots__ = tuple()


class Label(Stmt):
    __slots__ = ("name",)

    name: str

    def __init__(self, name: str, toks: List[Text]):
        self.name = name
        self.toks = toks

    def __repr__(self) -> str:  # pragma: no cover
        return f"Label({repr(self.name)})"

    def __eq__(self, other) -> bool:
        return type(self) is type(other) and (self.name == other.name)


class Op(Stmt):
    __slots__ = ("mnemonic", "arg")

    mnemonic: str
    arg: Union[str, int, None]

    def __init__(self, mnemonic: str, arg: Union[str, int, None], toks: List[Text]):
        self.mnemonic = mnemonic
        self.arg = arg
        self.toks = toks

    def __repr__(self) -> str:  # pragma: no cover
        return f"Op({repr(self.mnemonic)}, {repr(self.arg)})"

    def __eq__(self, other) -> bool:
        return type(self) is type(other) and (
            self.mnemonic == other.mnemonic and self.arg == other.arg
        )


class Val(Stmt):
    __slots__ = ("val",)

    val: int

    def __init__(self, val: int, tok: Text):
        self.val = val
        self.toks = [tok]

    def __repr__(self) -> str:  # pragma: no cover
        return f"Val({self.val})"

    def __eq__(self, other) -> bool:
        return type(self) is type(other) and (self.val == other.val)


def _require_text(tok: Token, msg: str) -> Text:
    if not isinstance(tok, Text):  # pragma: no cover
        raise RenderedError(msg, tok)
    return tok


class Parser:
    __slots__ = ("lexer", "tokens", "buf")

    lexer: Lexer
    tokens: Iterator[Token]
    buf: List[Token]

    def __init__(self, lexer: Lexer):
        self.lexer = lexer
        self.tokens = iter(lexer)
        self.buf = []

    @classmethod
    def from_str(cls, text: str) -> Parser:
        lexer = Lexer.from_str(text)
        return cls(lexer)

    @classmethod
    def from_buf(cls, buf: TextIO) -> Parser:
        lexer = Lexer(buf)
        return cls(lexer)

    def put(self, tok: Token) -> None:
        self.buf.append(tok)

    def get(self) -> Token:
        if len(self.buf) > 0:
            return self.buf.pop()
        else:
            try:
                return next(self.tokens)
            except StopIteration:
                raise EndOfTokens("end of tokens")

    def peek(self, n: int = 1) -> List[Token]:
        toks = []
        for _ in range(n):
            try:
                toks.append(self.get())
            except EndOfTokens:
                for tok in reversed(toks):
                    self.put(tok)
                raise

        for tok in reversed(toks):
            self.put(tok)

        return toks

    def move(self, n: int = 1) -> None:
        for _ in range(n):
            self.get()

    def parse_file(self) -> File:
        stmts = []
        while stmt := self.parse_stmt():
            stmts.append(stmt)

        self.parse_eof()

        return File(stmts)

    def parse_stmt(self) -> Optional[Stmt]:
        if label := self.parse_label():
            try:
                tok = self.peek(1)[0]
            except EndOfTokens:  # pragma: no cover
                return label

            # consume a newline if one exists
            if isinstance(tok, Newline):
                self.move(1)

            return label
        elif nullary_or_val := self.parse_nullary_or_val():
            return nullary_or_val
        else:
            return self.parse_unary()

    def parse_label(self) -> Optional[Label]:
        try:
            name, colon = self.peek(2)
        except EndOfTokens:
            return None

        if not isinstance(colon, Text) or colon.text != ":":
            return None

        self.move(2)

        name = _require_text(name, "expected a valid name")

        return Label(name.text, [name, colon])

    def parse_nullary_or_val(self) -> Union[Op, Val, None]:
        try:
            name_or_val, newline = self.peek(2)
        except EndOfTokens:
            return None

        if not isinstance(newline, Newline):
            return None

        self.move(2)

        name_or_val = _require_text(name_or_val, "expected a valid name or value")

        if NAME_RE.match(name_or_val.text):
            return Op(name_or_val.text, None, [name_or_val])
        elif VAL_RE.match(name_or_val.text):
            return Val(str_to_int(name_or_val.text), name_or_val)
        else:
            raise RenderedError(
                f"{repr(name_or_val.text)} is not a valid mnemonic or integer",
                name_or_val,
            )

    def parse_unary(self) -> Optional[Op]:
        try:
            mnemonic, name_or_val, newline = self.peek(3)
        except EndOfTokens:
            return None

        self.move(3)

        mnemonic = _require_text(mnemonic, "expected a valid name")
        name_or_val = _require_text(name_or_val, "expected a valid name or value")

        if not NAME_RE.match(mnemonic.text):
            raise RenderedError(
                f"{repr(mnemonic.text)} is not a valid mnemonic", mnemonic
            )
        if not isinstance(newline, Newline):
            raise RenderedError("expected end of line", newline)

        if VAL_RE.match(name_or_val.text):
            arg = str_to_int(name_or_val.text)
        elif NAME_RE.match(name_or_val.text):
            arg = name_or_val.text
        else:
            raise RenderedError(
                f"{repr(name_or_val.text)} is not a valid label or integer", name_or_val
            )

        return Op(mnemonic.text, arg, [mnemonic, name_or_val])

    def parse_eof(self) -> None:
        tok = self.get()
        if not isinstance(tok, Eof):  # pragma: no cover
            raise RenderedError("expected end of file", tok)
