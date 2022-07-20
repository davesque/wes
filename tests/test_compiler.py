from io import StringIO

import pytest

from das.compiler import Compiler
from das.exceptions import RenderedError
from das.lexer import Lexer
from das.parser import Parser


def test_compile_count() -> None:
    buf = StringIO(
        """
# Counts from 42 to 256 (zero really in 8 bits), then down from 255 to 1
# before halting

lda init

count_up:
  out
  add incr
  jc count_down  # jump to "count_down" if we overflowed
  jmp count_up

count_down:
  out
  sub incr
  jz end         # jump to "end" if we hit zero
  jmp count_down

end: hlt

init: 42
incr: 1
"""
    )
    lexer = Lexer(buf)
    parser = Parser(lexer)
    file = parser.parse_file()
    compiler = Compiler(file)

    assert list(compiler) == [26, 224, 43, 117, 97, 224, 59, 137, 101, 240, 42, 1]


def test_compile_fib() -> None:
    buf = StringIO(
        """
# Counts up in fibonacci numbers forever (with a lot of overflow)

loop:
  lda a
  out
  add b
  sta a

  lda b
  out
  add a
  sta b

  jmp loop

a: 1
b: 1
"""
    )
    lexer = Lexer(buf)
    parser = Parser(lexer)
    file = parser.parse_file()
    compiler = Compiler(file)

    assert list(compiler) == [25, 224, 42, 73, 26, 224, 41, 74, 96, 1, 1]


def test_compile_op_with_literal() -> None:
    buf = StringIO(
        """
lda 1
"""
    )
    lexer = Lexer(buf)
    parser = Parser(lexer)
    file = parser.parse_file()
    compiler = Compiler(file)

    assert list(compiler) == [17]


def test_compile_too_large() -> None:
    buf = StringIO(
        """
0
0
0
0
0
0
0
0
0
0
0
0
0
0
0
0
too_big
"""
    )
    lexer = Lexer(buf)
    parser = Parser(lexer)
    file = parser.parse_file()

    with pytest.raises(RenderedError) as excinfo:
        Compiler(file)

    assert "statement makes program too large" in excinfo.value.msg


def test_compile_duplicate_label() -> None:
    buf = StringIO(
        """
foo: 1
foo: 1
"""
    )
    lexer = Lexer(buf)
    parser = Parser(lexer)
    file = parser.parse_file()

    with pytest.raises(RenderedError) as excinfo:
        Compiler(file)

    assert "redefinition of label" in excinfo.value.msg


def test_compile_bad_unary_op() -> None:
    buf = StringIO(
        """
lda
"""
    )
    lexer = Lexer(buf)
    parser = Parser(lexer)
    file = parser.parse_file()

    with pytest.raises(RenderedError) as excinfo:
        list(Compiler(file))

    assert "requires an argument" in excinfo.value.msg


def test_compile_bad_nullary_op() -> None:
    buf = StringIO(
        """
nop 1
"""
    )
    lexer = Lexer(buf)
    parser = Parser(lexer)
    file = parser.parse_file()

    with pytest.raises(RenderedError) as excinfo:
        list(Compiler(file))

    assert "takes no argument" in excinfo.value.msg


def test_compile_bad_label() -> None:
    buf = StringIO(
        """
lda foo
"""
    )
    lexer = Lexer(buf)
    parser = Parser(lexer)
    file = parser.parse_file()

    with pytest.raises(RenderedError) as excinfo:
        list(Compiler(file))

    assert "unrecognized label" in excinfo.value.msg


def test_compile_big_op_arg() -> None:
    buf = StringIO(
        """
lda 16
"""
    )
    lexer = Lexer(buf)
    parser = Parser(lexer)
    file = parser.parse_file()

    with pytest.raises(RenderedError) as excinfo:
        list(Compiler(file))

    assert "is too large" in excinfo.value.msg


def test_compile_big_bare_literal() -> None:
    buf = StringIO(
        """
256
"""
    )
    lexer = Lexer(buf)
    parser = Parser(lexer)
    file = parser.parse_file()

    with pytest.raises(RenderedError) as excinfo:
        list(Compiler(file))

    assert "is too large" in excinfo.value.msg
