from .lexer import Token


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
        marker_str = " " * self.tok.col + "^" * len(self.tok.text)

        # fmt:off
        return f"""
at line {self.tok.line_num}, col {self.tok.col}:
{line}
{marker_str}

{self.msg}
"""[1:-1]
        # fmt: on
