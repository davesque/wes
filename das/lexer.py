from typing import Any, Callable, Iterator, TextIO

COMMENT_CHR = ";"


def _char_type(c: str) -> int:
    """
    Helper function for the low-level tokenizer.  All that matters is that this
    function outputs values that are considered different by the equality
    operator for different character types.
    """
    if c.isspace():
        return 0
    elif c == ":":
        return 1
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
    i = 0

    while i < len(s):
        curr_type = split_f(s[i])
        if curr_type != last_type:
            yield s[last_pos:i]
            last_pos = i

        last_type = curr_type
        i += 1

    yield s[last_pos:]


class Token:
    __slots__ = ("text", "line_start", "line_num", "col")

    text: str

    line_start: int
    line_num: int

    col: int

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
            "Token("
            f"{repr(self.text)}, "
            f"{self.line_start}, "
            f"{self.line_num}, "
            f"{self.col}"
            ")"
        )

    @property
    def is_newline(self) -> bool:
        return self.text == "\n"

    @property
    def is_eof(self) -> bool:
        return self.text == ""

    def __eq__(self, other) -> bool:
        return type(self) is type(other) and (
            self.text == other.text
            and self.line_start == other.line_start
            and self.line_num == other.line_num
            and self.col == other.col
        )


class Eof(Exception):
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

    def get_line(self) -> str:
        line = self.buf.readline()
        if len(line) == 0:
            raise Eof("eof")

        self.line_num += 1

        # we add this here to make some of the tokenization logic for semantic
        # newlines more simple
        if not line.endswith("\n"):
            line += "\n"

        return line

    def __iter__(self) -> Iterator[Token]:
        while True:
            # skip over empty lines and comment lines
            while True:
                try:
                    line = self.get_line()
                except Eof:
                    # eof token
                    yield Token(
                        "",
                        self.pos,
                        self.line_num + 1,
                        0,
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

                yield Token(
                    part,
                    self.pos,
                    self.line_num,
                    col,
                )

                col += len(part)

            # semantic newline token
            yield Token(
                "\n",
                self.pos,
                self.line_num,
                len(line) - 1,
            )

            self.pos += len(line)
