from io import StringIO

import pytest

from das.compiler import Compiler
from das.exceptions import RenderedError


def test_compile_count() -> None:
    compiler = Compiler.from_str(
        """
; Counts from 42 to 256 (zero really in 8 bits), then down from 255 to 1
; before halting

lda init

count_up:
  out
  add incr
  jc count_down  ; jump to "count_down" if we overflowed
  jmp count_up

count_down:
  out
  sub incr
  jz end         ; jump to "end" if we hit zero
  jmp count_down

end: hlt

init: 42
incr: 1
"""
    )
    assert list(compiler) == [26, 224, 43, 117, 97, 224, 59, 137, 101, 240, 42, 1]


def test_compile_fib() -> None:
    compiler = Compiler.from_str(
        """
; Counts up in fibonacci numbers forever (with a lot of overflow)

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
    assert list(compiler) == [25, 224, 42, 73, 26, 224, 41, 74, 96, 1, 1]


def test_compile_op_with_literal() -> None:
    compiler = Compiler.from_str("lda 1")
    assert list(compiler) == [17]


def test_compile_too_large() -> None:
    compiler = Compiler.from_str(
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
    with pytest.raises(RenderedError) as excinfo:
        list(compiler)

    assert "statement makes program too large" in excinfo.value.msg


def test_compile_duplicate_label() -> None:
    compiler = Compiler.from_str(
        """
foo: 1
foo: 1
"""
    )
    with pytest.raises(RenderedError) as excinfo:
        list(compiler)

    assert "redefinition of label" in excinfo.value.msg


def test_compile_bad_unary_op() -> None:
    compiler = Compiler.from_str("lda")
    with pytest.raises(RenderedError) as excinfo:
        list(compiler)

    assert "requires an argument" in excinfo.value.msg


def test_compile_bad_nullary_op() -> None:
    compiler = Compiler.from_str("nop 1")
    with pytest.raises(RenderedError) as excinfo:
        list(compiler)

    assert "takes no argument" in excinfo.value.msg


def test_compile_bad_label() -> None:
    compiler = Compiler.from_str("lda foo")
    with pytest.raises(RenderedError) as excinfo:
        list(compiler)

    assert "unrecognized label" in excinfo.value.msg


def test_compile_big_op_arg() -> None:
    compiler = Compiler.from_str("lda 16")
    with pytest.raises(RenderedError) as excinfo:
        list(compiler)

    assert "is too large" in excinfo.value.msg


def test_compile_big_bare_literal() -> None:
    compiler = Compiler.from_str("256")
    with pytest.raises(RenderedError) as excinfo:
        list(compiler)

    assert "is too large" in excinfo.value.msg


def test_compiler_from_str() -> None:
    assert list(Compiler.from_str("255")) == [255]


def test_compiler_from_buf() -> None:
    assert list(Compiler.from_buf(StringIO("255"))) == [255]
