from io import StringIO
from typing import Any, Callable, Optional, Tuple

import pytest

from wes.exceptions import Reset, Stop, TokenError
from wes.parser import (
    BinExpr as B,
    Expr,
    File,
    Label,
    Name as N,
    Node,
    Offset,
    Op,
    Parser,
    UnExpr as U,
    Val as V,
)

from .utils import Eq, Predicate, In


class MyNode(Node):
    __slots__ = ("foo", "bar")

    foo: Tuple[str, ...]
    bar: int

    def __init__(self, foo: Tuple[str, ...], bar: int, **kwargs: Any):
        self.foo = foo
        self.bar = bar

        super().__init__(**kwargs)


def test_node_slot_values() -> None:
    node = MyNode(("asdf", "zxcv"), 2)
    assert node.slot_values == (("asdf", "zxcv"), 2)


def test_node_repr() -> None:
    node = MyNode(("asdf", "zxcv"), 2)
    assert repr(node) == "MyNode(('asdf', 'zxcv'), 2)"


def test_node_eq() -> None:
    node1 = MyNode(("asdf", "zxcv"), 2)
    node2 = MyNode(("asdf", "zxcv"), 2)
    node3 = MyNode(("asdd", "zxcv"), 2)

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
            Op("lda", ("init",)),
            Label("count_up"),
            Op("out", ()),
            Op("add", ("incr",)),
            Op("jc", ("count_down",)),
            Op("jmp", ("count_up",)),
            Label("count_down"),
            Op("out", ()),
            Op("sub", ("incr",)),
            Op("jz", ("end",)),
            Op("jmp", ("count_down",)),
            Label("end"),
            Op("hlt", ()),
            Label("init"),
            V(42),
            Label("incr"),
            V(1),
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
            Label("loop"),
            Op("lda", ("a",)),
            Op("out", ()),
            Op("add", ("b",)),
            Op("sta", ("a",)),
            Op("lda", ("b",)),
            Op("out", ()),
            Op("add", ("a",)),
            Op("sta", ("b",)),
            Op("jmp", ("loop",)),
            Label("a"),
            V(1),
            Label("b"),
            V(1),
        )
    )


def test_parse_unary_with_val() -> None:
    parser = Parser.from_str("lda 1")
    file = parser.parse_file()
    assert file == File((Op("lda", (1,)),))


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
    assert file == File((Op("foo", ("bar", 42)),))


def test_parser_from_buf() -> None:
    buf = StringIO("foo")
    parser = Parser.from_buf(buf)

    assert parser.parse_file() == File((Op("foo", ()),))


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

    assert file == File((V(int_val),))


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
            Offset(0x8000, None),
            Label("start"),
            Op("lda", (42,)),
            Op("hlt", ()),
            Offset(0xFFFC, None),
            Op("word", ("start",)),
            Offset(0xFFFE, None),
            Op("word", (0,)),
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
    assert file == File((Op("lda", (1,)),))

    with pytest.raises(Reset) as excinfo:
        parser.get()

    assert excinfo.value.msg == "unexpected end of tokens"


# @pytest.mark.parametrize(
#     "file_txt,expected",
#     (
#         ("-2", UnExpr("-", V(2))),
#         ("-foo", UnExpr("-", Name("foo"))),
#         ("~2", UnExpr("~", V(2))),
#         ("~foo", UnExpr("~", Name("foo"))),
#         ("+2", None),
#     ),
# )
# def test_parse_un_expr(file_txt: str, expected: Optional[Expr]) -> None:
#     parser = Parser.from_str(file_txt)
#     actual = parser.parse_un_expr()

#     assert actual == expected


# @pytest.mark.parametrize(
#     "file_txt,check_msg",
#     (("-!!!", Eq("expected expression after unary operator '-'")),),
# )
# def test_parse_un_expr_error(file_txt: str, check_msg: Callable[[str], bool]) -> None:
#     parser = Parser.from_str(file_txt)

#     with pytest.raises(Stop) as excinfo:
#         parser.parse_un_expr()

#     assert check_msg(excinfo.value.msg)


@pytest.mark.parametrize(
    "method_name,file_txt,expected",
    (
        # ========= parse_atom =========
        ("parse_atom", "0", V(0)),
        ("parse_atom", "foo", N("foo")),
        ("parse_atom", "(foo)", N("foo")),
        ("parse_atom", "!!!", None),
        # hard failures
        ("parse_atom", "(!!!)", Eq("expected expression after '('")),
        # ========= parse_power =========
        ("parse_power", "!!!", None),  # returns `None` on fail
        ("parse_power", "0", V(0)),  # tries alternative
        ("parse_power", "0 ** 1", B(V(0), "**", V(1))),
        # associativity
        ("parse_power", "0 ** 1 ** 2", B(V(0), "**", B(V(1), "**", V(2)))),
        ("parse_power", "(0 ** 1) ** 2", B(B(V(0), "**", V(1)), "**", V(2))),
        # hard failures
        ("parse_power", "0 **", In("expected expression after '**'")),
        # ========= parse_factor =========
        ("parse_factor", "!!!", None),  # returns `None` on fail
        ("parse_factor", "0", V(0)),  # tries alternative
        ("parse_factor", "-0", U("-", V(0))),
        ("parse_factor", "~0", U("~", V(0))),
        # associativity
        ("parse_factor", "-~0", U("-", U("~", V(0)))),
        # neighboring operator precedence
        ("parse_factor", "-0 ** 1", U("-", B(V(0), "**", V(1)))),
        # hard failures
        ("parse_factor", "-", In("expected expression after '-'")),
        # ========= parse_term =========
        ("parse_term", "!!!", None),  # returns `None` on fail
        ("parse_term", "0", V(0)),  # tries alternative
        ("parse_term", "0 * 1", B(V(0), "*", V(1))),
        ("parse_term", "0 / 1", B(V(0), "/", V(1))),
        ("parse_term", "0 % 1", B(V(0), "%", V(1))),
        # associativity
        ("parse_term", "0 * 1 * 2", B(B(V(0), "*", V(1)), "*", V(2))),
        # neighboring operator precedence
        ("parse_term", "-0 * 1", B(U("-", V(0)), "*", V(1))),
        # hard failures
        ("parse_term", "0 *", In("expected expression after '*'")),
        # ========= parse_sum =========
        ("parse_sum", "!!!", None),  # returns `None` on fail
        ("parse_sum", "0", V(0)),  # tries alternative
        ("parse_sum", "0 + 1", B(V(0), "+", V(1))),
        ("parse_sum", "0 - 1", B(V(0), "-", V(1))),
        # associativity
        ("parse_sum", "0 + 1 + 2", B(B(V(0), "+", V(1)), "+", V(2))),
        # neighboring operator precedence
        ("parse_sum", "0 + 1 * 2", B(V(0), "+", B(V(1), "*", V(2)))),
        # hard failures
        ("parse_sum", "0 *", In("expected expression after '*'")),
        # ========= parse_shift =========
        ("parse_shift", "!!!", None),  # returns `None` on fail
        ("parse_shift", "0", V(0)),  # tries alternative
        ("parse_shift", "0 << 1", B(V(0), "<<", V(1))),
        ("parse_shift", "0 >> 1", B(V(0), ">>", V(1))),
        # associativity
        ("parse_shift", "0 >> 1 >> 2", B(B(V(0), ">>", V(1)), ">>", V(2))),
        # neighboring operator precedence
        ("parse_shift", "0 >> 1 + 2", B(V(0), ">>", B(V(1), "+", V(2)))),
        # hard failures
        ("parse_shift", "0 >>", In("expected expression after '>>'")),
        # ========= parse_and =========
        ("parse_and", "!!!", None),  # returns `None` on fail
        ("parse_and", "0", V(0)),  # tries alternative
        ("parse_and", "0 & 1", B(V(0), "&", V(1))),
        # associativity
        ("parse_and", "0 & 1 & 2", B(B(V(0), "&", V(1)), "&", V(2))),
        # neighboring operator precedence
        ("parse_and", "0 & 1 >> 2", B(V(0), "&", B(V(1), ">>", V(2)))),
        # hard failures
        ("parse_and", "0 &", In("expected expression after '&'")),
        # ========= parse_xor =========
        ("parse_xor", "!!!", None),  # returns `None` on fail
        ("parse_xor", "0", V(0)),  # tries alternative
        ("parse_xor", "0 ^ 1", B(V(0), "^", V(1))),
        # associativity
        ("parse_xor", "0 ^ 1 ^ 2", B(B(V(0), "^", V(1)), "^", V(2))),
        # neighboring operator precedence
        ("parse_xor", "0 ^ 1 & 2", B(V(0), "^", B(V(1), "&", V(2)))),
        # hard failures
        ("parse_xor", "0 ^", In("expected expression after '^'")),
        # ========= parse_expr =========
        ("parse_expr", "!!!", None),  # returns `None` on fail
        ("parse_expr", "0", V(0)),  # tries alternative
        ("parse_expr", "0 | 1", B(V(0), "|", V(1))),
        # associativity
        ("parse_expr", "0 | 1 | 2", B(B(V(0), "|", V(1)), "|", V(2))),
        # neighboring operator precedence
        ("parse_expr", "0 | 1 ^ 2", B(V(0), "|", B(V(1), "^", V(2)))),
        # hard failures
        ("parse_expr", "0 |", In("expected expression after '|'")),
    ),
)
def test_expr_parsers(method_name: str, file_txt: str, expected: Any) -> None:
    parser = Parser.from_str(file_txt)

    if expected is None or isinstance(expected, Node):
        actual = getattr(parser, method_name)()

        assert actual == expected
    elif isinstance(expected, Predicate):
        with pytest.raises(TokenError) as excinfo:
            getattr(parser, method_name)()

        assert expected(excinfo.value.msg)


@pytest.mark.parametrize(
    "file_txt,expected",
    (
        # basic binary expressions
        # ("0 - 0", B(z, "-", z)),
        # ("0 + 0", B(z, "+", z)),
        # ("0 * 0", B(z, "*", z)),
        # ("0 / 0", B(z, "/", z)),
        # ("0 >> 0", B(z, ">>", z)),
        # ("0 << 0", B(z, "<<", z)),
        # ("0 ^ 0", B(z, "^", z)),
        ("0 & 0", B(V(0), "&", V(0))),
        ("0 | 0", B(V(0), "|", V(0))),
        ("(0 & 1) | 2", B(B(V(0), "&", V(1)), "|", V(2))),
        # ("0 ** 0", B(z, "**", z)),
        # ("0 % 0", B(z, "%", z)),
        # operator precedence
        # ("0 * 0 + 0 * 0", B(B(z, "*", z), "+", B(z, "*", z))),
        # ("-foo", UnExpr("-", Name("foo", ()), ())),
        # ("~2", UnExpr("~", V(2, ()), ())),
        # ("~foo", UnExpr("~", Name("foo", ()), ())),
        # ("+2", None),
    ),
)
def test_parse_bin_expr(file_txt: str, expected: Optional[Expr]) -> None:
    parser = Parser.from_str(file_txt)
    actual = parser.parse_expr()

    assert actual == expected


# @pytest.mark.parametrize(
#     "file_txt,check_msg",
#     (("-!!!", Eq("expected expression after binary operator '-'")),),
# )
# def test_parse_bin_expr_error(file_txt: str, check_msg: Callable[[str], bool]) -> None:  # noqa: E501
#     parser = Parser.from_str(file_txt)

#     with pytest.raises(Stop) as excinfo:
#         parser.parse_bin_expr()

#     assert check_msg(excinfo.value.msg)


# @pytest.mark.parametrize(
#     "file_txt,expected",
#     (
#         ("2", V(2)),
#         ("0x2a", V(42)),
#         ("foo", Name("foo")),
#         ("(*&#@(*&@", None),
#     ),
# )
# def test_parse_atom(file_txt: str, expected: Optional[Expr]) -> None:
#     parser = Parser.from_str(file_txt)
#     actual = parser.parse_atom()

#     assert actual == expected
