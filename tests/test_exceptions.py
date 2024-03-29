import pytest

from wes.exceptions import Message
from wes.lexer import Lexer


def test_rendered_error_render_text() -> None:
    file_txt = "line one\nthe quick brown fox jumped over the lazy dogs"
    toks = tuple(Lexer.from_str(file_txt))
    e = Message("problem here", (toks[6],))

    # fmt: off
    assert e.render(file_txt) == """
at line 2, col 17:
the quick brown fox jumped over the lazy dogs
                ^^^

problem here
"""[1:-1]
    # fmt: on

    file_txt = "line one\nthe quick brown fox jumped over the lazy dogs\n"
    toks = tuple(Lexer.from_str(file_txt))
    e = Message("problem here", (toks[6],))

    # fmt: off
    assert e.render(file_txt) == """
at line 2, col 17:
the quick brown fox jumped over the lazy dogs
                ^^^

problem here
"""[1:-1]
    # fmt: on


def test_rendered_error_render_newline() -> None:
    file_txt = "test line"
    toks = tuple(Lexer.from_str(file_txt))
    e = Message("expected newline", (toks[2],))

    # fmt: off
    assert e.render(file_txt) == """
at line 1, col 10:
test line
         ^

expected newline
"""[1:-1]
    # fmt: on


def test_rendered_error_render_newline_with_nl() -> None:
    file_txt = "test line\n"
    toks = tuple(Lexer.from_str(file_txt))
    e = Message("expected newline", (toks[2],))

    # fmt: off
    assert e.render(file_txt) == """
at line 1, col 10:
test line
         ^

expected newline
"""[1:-1]
    # fmt: on


def test_rendered_error_render_eof() -> None:
    file_txt = "test line"
    toks = tuple(Lexer.from_str(file_txt))
    e = Message("expected eof", (toks[3],))

    # fmt: off
    assert e.render(file_txt) == """
at line 1, col 10:
test line
         ^

expected eof
"""[1:-1]
    # fmt: on


def test_rendered_error_render_eof_with_nl() -> None:
    file_txt = "test line\n"
    toks = tuple(Lexer.from_str(file_txt))
    e = Message("expected eof", (toks[3],))

    # fmt: off
    assert e.render(file_txt) == r"""
at line 1, col 11:
test line
         ^

expected eof
"""[1:-1]
    # fmt: on


def test_rendered_error_multiple_tokens() -> None:
    file_txt = "line one\nthe quick brown fox jumped over the lazy dogs"
    toks = tuple(Lexer.from_str(file_txt))

    e = Message("problem here", toks[5:8])
    # fmt: off
    assert e.render(file_txt) == """
at line 2, col 11:
the quick brown fox jumped over the lazy dogs
          ^^^^^^^^^^^^^^^^

problem here
"""[1:-1]
    # fmt: on

    e = Message("problem here", (toks[5], toks[7]))
    # fmt: off
    assert e.render(file_txt) == """
at line 2, col 11:
the quick brown fox jumped over the lazy dogs
          ^^^^^^^^^^^^^^^^

problem here
"""[1:-1]
    # fmt: on

    e = Message("problem here", toks[1:3])
    # fmt: off
    assert e.render(file_txt) == """
at line 1, col 6:
line one
     ^^^

problem here
"""[1:-1]
    # fmt: on

    file_txt = "line one\n"
    toks = tuple(Lexer.from_str(file_txt))

    e = Message("problem here", toks[1:])
    # fmt: off
    assert e.render(file_txt) == """
at line 1, col 6:
line one
     ^^^

problem here
"""[1:-1]
    # fmt: on

    e = Message("problem here", toks[2:])
    # fmt: off
    assert e.render(file_txt) == """
at line 1, col 9:
line one
        ^

problem here
"""[1:-1]
    # fmt: on


def test_rendered_error_value_errors() -> None:
    with pytest.raises(ValueError, match="expected one or more tokens"):
        Message("foo", ())

    file_txt = "line one\nthe quick brown fox jumped over the lazy dogs"
    toks = tuple(Lexer.from_str(file_txt))

    with pytest.raises(ValueError, match="tokens not from same line"):
        Message("foo", toks[0:5])
