from io import StringIO
from typing import Optional, Tuple

import pytest

from wes.exceptions import Reset, Stop
from wes.lexer import Text
from wes.parser import Expr, File, Label, Node, Offset, Op, Parser, Val


class MyNode(Node):
    __slots__ = ("foo", "bar")

    foo: Tuple[str, ...]
    bar: int

    def __init__(self, foo: Tuple[str, ...], bar: int, toks: Tuple[Text, ...]):
        self.foo = foo
        self.bar = bar

        super().__init__(toks)


def test_node_slot_values() -> None:
    node = MyNode(("asdf", "zxcv"), 2, ())
    assert node.slot_values == (("asdf", "zxcv"), 2)


def test_node_repr() -> None:
    node = MyNode(("asdf", "zxcv"), 2, ())
    assert repr(node) == "MyNode(('asdf', 'zxcv'), 2)"


def test_node_eq() -> None:
    node1 = MyNode(("asdf", "zxcv"), 2, ())
    node2 = MyNode(("asdf", "zxcv"), 2, ())
    node3 = MyNode(("asdd", "zxcv"), 2, ())

    assert node1 == node2
    assert node1 != node3
    assert node1 != 2


@pytest.fixture
def count_parser() -> Parser:
    return Parser.from_str(
        """
lda init
loop:
  out
  add incr
  jmp loop
init: 0
incr: 1
"""
    )


def test_parse_count() -> None:
    parser = Parser.from_str(
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
    file = parser.parse_file()
    assert file == File(
        (
            Op("lda", ("init",), ()),
            Label("count_up", ()),
            Op("out", (), ()),
            Op("add", ("incr",), ()),
            Op("jc", ("count_down",), ()),
            Op("jmp", ("count_up",), ()),
            Label("count_down", ()),
            Op("out", (), ()),
            Op("sub", ("incr",), ()),
            Op("jz", ("end",), ()),
            Op("jmp", ("count_down",), ()),
            Label("end", ()),
            Op("hlt", (), ()),
            Label("init", ()),
            Val(42, ()),
            Label("incr", ()),
            Val(1, ()),
        )
    )


def test_parse_fib() -> None:
    parser = Parser.from_str(
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
    file = parser.parse_file()
    assert file == File(
        (
            Label("loop", ()),
            Op("lda", ("a",), ()),
            Op("out", (), ()),
            Op("add", ("b",), ()),
            Op("sta", ("a",), ()),
            Op("lda", ("b",), ()),
            Op("out", (), ()),
            Op("add", ("a",), ()),
            Op("sta", ("b",), ()),
            Op("jmp", ("loop",), ()),
            Label("a", ()),
            Val(1, ()),
            Label("b", ()),
            Val(1, ()),
        )
    )


def test_parse_unary_with_val() -> None:
    parser = Parser.from_str("lda 1")
    file = parser.parse_file()
    assert file == File((Op("lda", (1,), ()),))


def test_parse_nullary_or_val_invalid() -> None:
    parser = Parser.from_str("!!!")

    with pytest.raises(Stop) as excinfo:
        parser.parse_file()

    assert "is not a valid name or integer" in excinfo.value.msg


def test_parse_unary_invalid_mnemonic() -> None:
    parser = Parser.from_str("!!! blah")

    with pytest.raises(Stop) as excinfo:
        parser.parse_file()

    assert "is not a valid name" in excinfo.value.msg


def test_parse_unary_invalid_op_arg() -> None:
    parser = Parser.from_str("blah !!!")

    with pytest.raises(Stop) as excinfo:
        parser.parse_file()

    assert "is not a valid name or integer" in excinfo.value.msg


def test_parse_binary_expected_comma() -> None:
    parser = Parser.from_str("foo bar baz")

    with pytest.raises(Stop) as excinfo:
        parser.parse_file()

    assert "expected ','" in excinfo.value.msg


def test_parse_binary_expected_text() -> None:
    parser = Parser.from_str("foo bar,")

    with pytest.raises(Stop) as excinfo:
        parser.parse_file()

    assert "unexpected end of line" in excinfo.value.msg


def test_parse_binary_expected_newline() -> None:
    parser = Parser.from_str("foo bar, baz bing")

    with pytest.raises(Stop) as excinfo:
        parser.parse_file()

    assert "expected end of line" in excinfo.value.msg


def test_parse_binary_expected_mnemonic() -> None:
    parser = Parser.from_str("!!! bar, baz")

    with pytest.raises(Stop) as excinfo:
        parser.parse_file()

    assert "is not a valid name" in excinfo.value.msg


def test_parse_binary() -> None:
    parser = Parser.from_str("foo bar, 42")
    file = parser.parse_file()
    assert file == File((Op("foo", ("bar", 42), ()),))


def test_parser_from_buf() -> None:
    buf = StringIO("foo")
    parser = Parser.from_buf(buf)

    assert parser.parse_file() == File((Op("foo", (), ()),))


@pytest.mark.parametrize(
    "int_repr,int_val",
    (
        ("1_000_000_000", 1_000_000_000),
        ("0b1000_0000", 0b1000_0000),
        ("0o52_52", 0o52_52),
        ("0x52_52", 0x52_52),
    ),
)
def test_parse_underscore_digit_grouping(int_repr: str, int_val: int) -> None:
    parser = Parser.from_str(int_repr)
    file = parser.parse_file()

    assert file == File((Val(int_val, ()),))


def test_parse_offsets() -> None:
    parser = Parser.from_str(
        """
0x8000:

start:
  lda 42

hlt

0xfffc:
  word start
0xfffe:
  word 0
"""
    )
    file = parser.parse_file()
    assert file == File(
        (
            Offset(0x8000, None, ()),
            Label("start", ()),
            Op("lda", (42,), ()),
            Op("hlt", (), ()),
            Offset(0xFFFC, None, ()),
            Op("word", ("start",), ()),
            Offset(0xFFFE, None, ()),
            Op("word", (0,), ()),
        )
    )


def test_invalid_label_name() -> None:
    parser = Parser.from_str("foo!#@$: 0")
    label = parser.parse_label()

    assert label is None


def test_invalid_forward_offset_val() -> None:
    parser = Parser.from_str("+foo: 0")
    label = parser.parse_relative()

    assert label is None


def test_invalid_backward_offset_val() -> None:
    parser = Parser.from_str("-foo: 0")
    label = parser.parse_relative()

    assert label is None


def test_parser_get_error() -> None:
    parser = Parser.from_str("lda 1")
    file = parser.parse_file()
    assert file == File((Op("lda", (1,), ()),))

    with pytest.raises(Reset) as excinfo:
        parser.get()

    assert excinfo.value.msg == "unexpected end of tokens"
