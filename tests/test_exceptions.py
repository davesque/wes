from io import StringIO

from das.exceptions import RenderedError
from das.lexer import Lexer


def test_rendered_error_render() -> None:
    toks = list(Lexer(StringIO("the quick brown fox jumped over the lazy dogs")))
    e = RenderedError("problem here", toks[3])

    # fmt: off
    assert e.render() == """
at line 1, col 16:
the quick brown fox jumped over the lazy dogs
                ^^^

problem here
"""[1:-1]
    # fmt: on
