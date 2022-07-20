from typing import Iterator, TextIO


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


def tokenize(buf: str) -> Iterator[str]:
    """
    Split a string into regions of differing character types.
    """
    if len(buf) == 0:
        return

    last_pos = 0
    last_type = _char_type(buf[0])
    i = 0

    while i < len(buf):
        curr_type = _char_type(buf[i])
        if curr_type != last_type:
            yield buf[last_pos:i]
            last_pos = i

        last_type = curr_type
        i += 1

    yield buf[last_pos:]


class Token:
    __slots__ = ("text", "start", "end", "line", "line_start", "line_num", "col")

    text: str

    start: int
    end: int

    line: str
    line_start: int
    line_num: int

    col: int

    def __init__(
        self,
        text: str,
        start: int,
        end: int,
        line: str,
        line_start: int,
        line_num: int,
        col: int,
    ):
        self.text = text

        self.start = start
        self.end = end

        self.line = line
        self.line_start = line_start
        self.line_num = line_num

        self.col = col

    def __repr__(self) -> str:
        return (
            "Token("
            f"{repr(self.text)}, "
            f"{self.start}, "
            f"{self.end}, "
            f"{repr(self.line)}, "
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
            and self.start == other.start
            and self.end == other.end
            and self.line == other.line
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

        # we add this here to make some of the tokenization logic for semantic
        # newlines more simple
        if not line.endswith("\n"):
            line += "\n"

        self.line_num += 1
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
                        self.pos,
                        "",
                        self.pos,
                        self.line_num + 1,
                        0,
                    )
                    return

                stripped = line.strip()
                is_empty_line = len(stripped) == 0 or stripped.startswith("#")

                if not is_empty_line:
                    break

                self.pos += len(line)

            col = 0
            for part in tokenize(line):
                if part.isspace():
                    col += len(part)
                    continue
                elif part.startswith("#"):
                    # We've hit a comment.  No more tokens coming from this
                    # line.
                    break

                yield Token(
                    part,
                    self.pos + col,
                    self.pos + col + len(part),
                    line,
                    self.pos,
                    self.line_num,
                    col,
                )

                col += len(part)

            # semantic newline token
            yield Token(
                "\n",
                self.pos + len(line) - 1,
                self.pos + len(line),
                line,
                self.pos,
                self.line_num,
                len(line) - 1,
            )

            self.pos += len(line)
