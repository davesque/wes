import pytest

from wes.compilers.sap import SapCompiler
from wes.exceptions import Message


def test_compile_count() -> None:
    compiler = SapCompiler.from_str(
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
    compiler = SapCompiler.from_str(
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
    compiler = SapCompiler.from_str("lda 1")
    assert list(compiler) == [17]


def test_compile_bad_unary_op() -> None:
    compiler = SapCompiler.from_str("lda")
    with pytest.raises(Message) as excinfo:
        list(compiler)

    assert "takes one argument" in excinfo.value.msg


def test_compile_bad_nullary_op() -> None:
    compiler = SapCompiler.from_str("nop 1")
    with pytest.raises(Message) as excinfo:
        list(compiler)

    assert "takes no argument" in excinfo.value.msg


def test_compile_bad_label() -> None:
    compiler = SapCompiler.from_str("lda foo")
    with pytest.raises(Message) as excinfo:
        list(compiler)

    assert "name 'foo' is not bound" in excinfo.value.msg


def test_compile_big_op_arg() -> None:
    compiler = SapCompiler.from_str("lda 16")
    with pytest.raises(Message) as excinfo:
        list(compiler)

    assert "is too large" in excinfo.value.msg


def test_compile_big_bare_literal() -> None:
    compiler = SapCompiler.from_str("256")
    with pytest.raises(Message) as excinfo:
        list(compiler)

    assert "is too large" in excinfo.value.msg


def test_compile_unrecognized_instruction() -> None:
    compiler = SapCompiler.from_str("foo")
    with pytest.raises(Message) as excinfo:
        list(compiler)

    assert "unrecognized instruction" in excinfo.value.msg
