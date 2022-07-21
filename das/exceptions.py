from .lexer import Eof, Newline, Text, Token


class ParseError(Exception):
    pass


class EndOfTokens(ParseError):
    pass


class RenderedError(ParseError):
    def __init__(self, msg: str, tok: Token):
        self.msg = msg
        self.tok = tok

    @staticmethod
    def _get_line(file_txt: str, line_start: int) -> str:
        line_end = file_txt.find("\n", line_start)
        if line_end == -1:
            line_end = len(file_txt)

        return file_txt[line_start:line_end]

    def render(self, file_txt: str) -> str:
        line = self._get_line(file_txt, self.tok.line_start)

        if isinstance(self.tok, Text):
            marker = "^" * len(self.tok.text)
        elif isinstance(self.tok, (Newline, Eof)):
            marker = "^"
        else:  # pragma: no cover
            raise Exception("invariant")
        marker_str = " " * self.tok.col + marker

        # fmt:off
        return f"""
at line {self.tok.line_num}, col {self.tok.col}:
{line}
{marker_str}

{self.msg}
"""[1:-1]
        # fmt: on
