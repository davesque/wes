from typing import Tuple

from das.lexer import Eof, Newline, Text, Token


class ParserError(Exception):
    pass


class EndOfTokens(ParserError):
    pass


class WrongTokens(ParserError):
    pass


class RenderedError(Exception):
    def __init__(self, msg: str, toks: Tuple[Token, ...]):
        if len(toks) == 0:
            raise ValueError("expected one or more tokens")

        line_num = toks[0].line_num
        if any(t.line_num != line_num for t in toks):
            raise ValueError("tokens not from same line")

        self.msg = msg
        self.toks = toks

    @staticmethod
    def _get_line(file_txt: str, line_start: int) -> str:
        line_end = file_txt.find("\n", line_start)
        if line_end == -1:
            line_end = len(file_txt)
        else:
            line_end += 1

        return file_txt[line_start:line_end]

    def render(self, file_txt: str) -> str:
        fst, lst = self.toks[0], self.toks[-1]
        line = self._get_line(file_txt, fst.line_start).strip()

        marker_start = min(len(line), fst.col)
        if len(self.toks) == 1:
            if isinstance(fst, Text):
                marker_len = len(fst.text)
            elif isinstance(fst, (Newline, Eof)):
                marker_len = 1
            else:  # pragma: no cover
                raise Exception("invariant")
        else:
            if isinstance(lst, Text):
                marker_end = lst.col + len(lst.text)
            elif isinstance(lst, (Newline, Eof)):
                marker_end = min(len(line), lst.col)
            else:  # pragma: no cover
                raise Exception("invariant")
            marker_len = max(1, marker_end - marker_start)

        marker_string = " " * marker_start + "^" * marker_len

        # fmt:off
        return f"""
at line {fst.line_num}, col {fst.col}:
{line}
{marker_string}

{self.msg}
"""[1:-1]
        # fmt: on
