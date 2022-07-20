from .lexer import Token


class ParseError(Exception):
    pass


class EndOfTokens(ParseError):
    pass


class RenderedError(ParseError):
    def __init__(self, msg: str, tok: Token):
        self.msg = msg
        self.tok = tok

    def render(self) -> str:
        start = self.tok.start
        end = self.tok.end
        col = self.tok.col

        marker_str = " " * col + "^" * (end - start)

        # fmt:off
        return f"""
at line {self.tok.line_num}, col {self.tok.col}:
{self.tok.line.rstrip()}
{marker_str}

{self.msg}
"""[1:-1]
        # fmt: on
