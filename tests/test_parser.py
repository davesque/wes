from io import StringIO

import pytest

from das.exceptions import Stop
from das.parser import File, Label, Op, Parser, Val


@pytest.fixture
def count_parser() -> Parser:
    return Parser.from_str("""
lda init
loop:
  out
  add incr
  jmp loop
init: 0
incr: 1
""")


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


def test_parser_mark_api(count_parser: Parser) -> None:
    parser = count_parser

    parser.mark()
    assert parser.expect().text == "lda"
    assert parser.expect().text == "init"
    parser.reset()
    assert parser.expect().text == "lda"
    assert parser.expect().text == "init"


def test_parser_nested_reset(count_parser: Parser) -> None:
    parser = count_parser

    parser.mark()
    assert parser.expect().text == "lda"
    parser.mark()
    assert parser.expect().text == "init"
    parser.reset()
    assert parser.expect().text == "init"
    parser.reset()
    assert parser.expect().text == "lda"
    assert parser.expect().text == "init"


def test_parser_nested_unmark(count_parser: Parser) -> None:
    parser = count_parser

    parser.mark()
    assert parser.expect().text == "lda"
    parser.mark()
    assert parser.expect().text == "init"
    parser.unmark()
    assert parser.expect_newline()
    parser.reset()
    assert parser.expect().text == "lda"
    assert parser.expect().text == "init"


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
