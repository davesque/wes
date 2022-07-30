from __future__ import annotations

from io import StringIO
from typing import Any, Callable, Iterator, TextIO

COMMENT_CHR = ";"


def _char_type(c: str) -> Any:
    """
    Helper function for the low-level tokenizer.  All that matters is that this
    function outputs values that are considered different by the equality
    operator for different character regions.
    """
    if c.isspace():
        return 0
    elif c in ":,+-[]":
        return float("nan")
    else:
        return 1


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


class EndOfBuffer(Exception):
    pass


class Lexer:
    __slots__ = ("buf", "line_num", "pos")

    buf: TextIO

    line_num: int
    pos: int

    def __init__(self, buf: TextIO):
        self.buf = buf

        self.line_num = 0
        self.pos = 0

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

                yield Text(part, self.pos, self.line_num, col)

                col += len(part)

            # semantic newline token
            yield Newline(
                self.pos,
                self.line_num,
                len(line) - 1 if line[-1] == "\n" else len(line),
            )

            self.pos += len(line)
