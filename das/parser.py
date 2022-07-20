from __future__ import annotations

import re
from typing import Iterator, List, Optional, Union

from .exceptions import DasSyntaxError, EndOfTokens
from .lexer import Lexer, Token
from .utils import str_to_int

NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
VAL_RE = re.compile(r"^(0b[01]+|0o[0-7]+|[0-9]+|0x[a-fA-F0-9]+)$")


class Node:
    __slots__ = ("toks",)

    toks: List[Token]


class File(Node):
    __slots__ = ("stmts",)

    stmts: List[Stmt]

    def __init__(self, stmts: List[Stmt]):
        self.stmts = stmts

        self.toks = []
        for stmt in stmts:
            self.toks.extend(stmt.toks)

    def __repr__(self) -> str:
        return f"File({repr(self.stmts)})"


class Stmt(Node):
    __slots__ = tuple()


class Label(Stmt):
    __slots__ = ("name",)

    name: str

    def __init__(self, name: str, toks: List[Token]):
        self.name = name
        self.toks = toks

    def __repr__(self) -> str:
        return f"Label({repr(self.name)})"


class Op(Stmt):
    __slots__ = ("mnemonic", "arg")

    mnemonic: str
    arg: Union[str, int, None]

    def __init__(self, mnemonic: str, arg: Union[str, int, None], toks: List[Token]):
        self.mnemonic = mnemonic
        self.arg = arg
        self.toks = toks

    def __repr__(self) -> str:
        return f"Op({repr(self.mnemonic)}, {repr(self.arg)})"


class Val(Stmt):
    __slots__ = ("val",)

    val: int

    def __init__(self, val: int, tok: Token):
        self.val = val
        self.toks = [tok]

    def __repr__(self) -> str:
        return f"Val({self.val})"


class Parser:
    __slots__ = ("lex", "tokens", "buf")

    lex: Lexer
    tokens: Iterator[Token]
    buf: List[Token]

    def __init__(self, lex: Lexer):
        self.lex = lex
        self.tokens = iter(lex)
        self.buf = []

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
            except EndOfTokens:
                return label

            # consume a newline if one exists
            if tok.is_newline:
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

        if colon.text != ":":
            return None

        self.move(2)
        return Label(name.text, [name, colon])

    def parse_nullary_or_val(self) -> Union[Op, Val, None]:
        try:
            name_or_val, newline = self.peek(2)
        except EndOfTokens:
            return None

        if not newline.is_newline:
            return None

        self.move(2)

        if NAME_RE.match(name_or_val.text):
            return Op(name_or_val.text, None, [name_or_val])
        elif VAL_RE.match(name_or_val.text):
            return Val(str_to_int(name_or_val.text), name_or_val)
        else:
            raise DasSyntaxError(f"{repr(name_or_val.text)} is not a valid mnemonic or integer", name_or_val)

    def parse_unary(self) -> Optional[Op]:
        try:
            name, name_or_val, newline = self.peek(3)
        except EndOfTokens:
            return None

        self.move(3)

        if not NAME_RE.match(name.text):
            raise DasSyntaxError(f"{repr(name.text)} is not a valid name", name)
        if not newline.is_newline:
            raise DasSyntaxError("expected end of line", newline)

        if VAL_RE.match(name_or_val.text):
            arg = str_to_int(name_or_val.text)
        elif NAME_RE.match(name_or_val.text):
            arg = name_or_val.text
        else:
            raise DasSyntaxError(f"{repr(name_or_val.text)} is not a valid label or integer", name_or_val)

        return Op(name.text, arg, [name, name_or_val])

    def parse_eof(self) -> None:
        tok = self.get()
        if not tok.is_eof:
            raise DasSyntaxError("expected end of file", tok)
