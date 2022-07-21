from io import StringIO

from das.exceptions import RenderedError
from das.lexer import Lexer


def test_rendered_error_render() -> None:
    file_txt = "line one\nthe quick brown fox jumped over the lazy dogs"
    toks = list(Lexer(StringIO(file_txt)))
    e = RenderedError("problem here", toks[6])

    # fmt: off
    assert e.render(file_txt) == """
at line 2, col 16:
the quick brown fox jumped over the lazy dogs
                ^^^

problem here
"""[1:-1]
    # fmt: on

    file_txt = "line one\nthe quick brown fox jumped over the lazy dogs\n"
    toks = list(Lexer(StringIO(file_txt)))
    e = RenderedError("problem here", toks[6])

    # fmt: off
    assert e.render(file_txt) == """
at line 2, col 16:
the quick brown fox jumped over the lazy dogs
                ^^^

problem here
"""[1:-1]
    # fmt: on
