from typing import List, Union

import pytest

from wes.compilers.sap import CompileSap
from wes.exceptions import Message

from ..utils import Eq, Predicate


@pytest.mark.parametrize(
    "file_txt,expected",
    (("ldi 0x10", Eq("evaluated result '16' is too large")),),
)
def test_sap_instructions(file_txt: str, expected: Union[List[int], Predicate]) -> None:
    compiler = CompileSap.from_str(file_txt)

    if isinstance(expected, Predicate):
        with pytest.raises(Message) as excinfo:
            list(compiler)

        assert expected(excinfo.value.msg)
    else:
        assert list(compiler) == expected


def test_compile_count() -> None:
    compiler = CompileSap.from_str(
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
    compiler = CompileSap.from_str(
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
    compiler = CompileSap.from_str("lda 1")
    assert list(compiler) == [17]


def test_compile_bad_unary_op() -> None:
    compiler = CompileSap.from_str("lda")
    with pytest.raises(Message) as excinfo:
        list(compiler)

    assert "takes one argument" in excinfo.value.msg


def test_compile_bad_nullary_op() -> None:
    compiler = CompileSap.from_str("nop 1")
    with pytest.raises(Message) as excinfo:
        list(compiler)

    assert "takes no argument" in excinfo.value.msg


def test_compile_bad_label() -> None:
    compiler = CompileSap.from_str("lda foo")
    with pytest.raises(Message) as excinfo:
        list(compiler)

    assert "name 'foo' is not bound" in excinfo.value.msg


def test_compile_big_op_arg() -> None:
    compiler = CompileSap.from_str("lda 16")
    with pytest.raises(Message) as excinfo:
        list(compiler)

    assert "is too large" in excinfo.value.msg


def test_compile_big_bare_literal() -> None:
    compiler = CompileSap.from_str("256")
    with pytest.raises(Message) as excinfo:
        list(compiler)

    assert "is too large" in excinfo.value.msg


def test_compile_unrecognized_instruction() -> None:
    compiler = CompileSap.from_str("foo")
    with pytest.raises(Message) as excinfo:
        list(compiler)

    assert "unrecognized instruction" in excinfo.value.msg
