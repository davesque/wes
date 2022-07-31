from __future__ import annotations

from io import StringIO
from typing import Any, Callable, Iterator, List, TextIO

from wes.exceptions import EndOfTokens, Message

COMMENT_CHR = ";"

# Continuous runs of these characters will be joined into one token.  This
# simplifies parsing of the '**', '<<', and '>>' operators.
JOINED = "*<>"

# Continuous runs of these characters will all be treated as separate tokens.
DISJOINED = "-~+/^&|%:,[]()"


def _char_type(c: str) -> Any:
    """
    Helper function for the low-level tokenizer.  All that matters is that this
    function outputs values that are considered different by the equality
    operator for different character regions.
    """
    if c.isspace():
        return 0
    elif c in JOINED:
        return 1
    elif c in DISJOINED:
        return float("nan")
    else:
        return 2


def tokenize(s: str, *, split_f: Callable[[str], Any] = _char_type) -> Iterator[str]:
    """
    Split a string into regions of differing character types.
    """
    if len(s) == 0:
        return

    last_pos = 0
    last_type = split_f(s[0])
    i = 1

    while i < len(s):
        curr_type = split_f(s[i])
        if curr_type != last_type:
            yield s[last_pos:i]
            last_pos = i

        last_type = curr_type
        i += 1

    yield s[last_pos:]


class Token:
    __slots__ = ("line_start", "line_num", "col")

    line_start: int
    line_num: int
    col: int

    def __init__(
        self,
        line_start: int,
        line_num: int,
        col: int,
    ):
        self.line_start = line_start
        self.line_num = line_num
        self.col = col

    def __eq__(self, other: Any) -> bool:
        return type(self) is type(other) and (
            self.line_start == other.line_start
            and self.line_num == other.line_num
            and self.col == other.col
        )


class Text(Token):
    __slots__ = ("text",)

    text: str

    def __init__(
        self,
        text: str,
        line_start: int,
        line_num: int,
        col: int,
    ):
        self.text = text

        self.line_start = line_start
        self.line_num = line_num
        self.col = col

    def __repr__(self) -> str:  # pragma: no cover
        return (
            "Text("
            f"{repr(self.text)}, "
            f"{self.line_start}, "
            f"{self.line_num}, "
            f"{self.col}"
            ")"
        )

    def __eq__(self, other: Any) -> bool:
        return type(self) is type(other) and (
            self.text == other.text
            and self.line_start == other.line_start
            and self.line_num == other.line_num
            and self.col == other.col
        )


class Newline(Token):
    def __repr__(self) -> str:  # pragma: no cover
        return f"Newline({self.line_start}, {self.line_num}, {self.col})"


class Eof(Token):
    def __repr__(self) -> str:  # pragma: no cover
        return f"Eof({self.line_start}, {self.line_num}, {self.col})"


class LexerError(Exception):
    pass


class EndOfBuffer(Exception):
    pass


class Lexer:
    __slots__ = ("buf", "line_num", "pos", "delims")

    buf: TextIO

    line_num: int
    pos: int
    delims: List[Text]

    DELIM_PAIRS = {
        "[": "]",
        "(": ")",
    }

    def __init__(self, buf: TextIO):
        self.buf = buf

        self.line_num = 0
        self.pos = 0
        self.delims = []

    def push_delim(self, tok: Text) -> None:
        self.delims.append(tok)

    def pop_delim(self, tok: Text) -> None:
        if len(self.delims) == 0:
            raise Message(f"unmatched closing delimiter '{tok.text}'", (tok,))

        prev = self.delims[-1].text
        expected = self.DELIM_PAIRS[prev]
        if tok.text != expected:
            raise Message(
                f"delimiter mistmatch: expected '{expected}', got '{tok.text}'",
                (tok,),
            )

        self.delims.pop()

    @classmethod
    def from_str(cls, text: str) -> Lexer:
        buf = StringIO(text)
        return cls(buf)

    def get_line(self) -> str:
        line = self.buf.readline()
        if len(line) == 0:
            raise EndOfBuffer()

        self.line_num += 1
        return line

    def __iter__(self) -> Iterator[Token]:
        line = None

        while True:
            # skip over empty lines and comment lines
            while True:
                try:
                    line = self.get_line()
                except EndOfBuffer:
                    if line is None:
                        line = ""

                    if len(self.delims) > 0:
                        tok = self.delims[-1]
                        raise Message(
                            f"unmatched opening delimiter '{tok.text}'",
                            (tok,),
                        )
                    yield Eof(
                        self.pos - len(line),
                        self.line_num,
                        # `line` here is the previous line since the expression
                        # to the right of the assignment operator raised an
                        # exception
                        len(line),
                    )
                    return

                stripped = line.strip()
                is_empty_line = len(stripped) == 0 or stripped.startswith(COMMENT_CHR)

                if not is_empty_line:
                    break

                self.pos += len(line)

            col = 0
            for part in tokenize(line):
                if part.isspace():
                    col += len(part)
                    continue
                elif part.startswith(COMMENT_CHR):
                    # We've hit a comment.  No more tokens coming from this
                    # line.
                    break

                tok = Text(part, self.pos, self.line_num, col)

                if part in ("[", "("):
                    self.push_delim(tok)
                elif part in ("]", ")"):
                    self.pop_delim(tok)

                yield tok
                col += len(part)

            # no semantic newline if we're inside of delimiters
            if len(self.delims) == 0:
                yield Newline(
                    self.pos,
                    self.line_num,
                    len(line) - 1 if line[-1] == "\n" else len(line),
                )

            self.pos += len(line)


class TokenStream:
    __slots__ = ("toks", "hist", "i")

    toks: Iterator[Token]
    hist: List[Token]
    i: int

    def __init__(self, lexer: Lexer):
        self.toks = iter(lexer)
        self.hist = []
        self.i = 0

    def get(self) -> Token:
        if self.i < len(self.hist):
            tok = self.hist[self.i]
        else:
            try:
                tok = next(self.toks)
            except StopIteration:
                raise EndOfTokens("end of tokens")
            self.hist.append(tok)

        self.i += 1
        return tok

    def mark(self) -> int:
        return self.i

    def reset(self, i: int) -> None:
        self.i = i
