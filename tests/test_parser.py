from io import StringIO
from typing import Any, Dict, Tuple, cast

import pytest

from wes.exceptions import Message, Stop, TokenError
from wes.parser import BinExpr as B
from wes.parser import Const, Expr, File, Label
from wes.parser import Name as N
from wes.parser import Node, Offset, Op, Parser
from wes.parser import UnExpr as U
from wes.parser import Val as V

from .utils import Eq, In, Predicate


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
            Op("lda", (N("init"),)),
            Label("count_up"),
            N("out"),
            Op("add", (N("incr"),)),
            Op("jc", (N("count_down"),)),
            Op("jmp", (N("count_up"),)),
            Label("count_down"),
            N("out"),
            Op("sub", (N("incr"),)),
            Op("jz", (N("end"),)),
            Op("jmp", (N("count_down"),)),
            Label("end"),
            N("hlt"),
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
            Op("lda", (N("a"),)),
            N("out"),
            Op("add", (N("b"),)),
            Op("sta", (N("a"),)),
            Op("lda", (N("b"),)),
            N("out"),
            Op("add", (N("a"),)),
            Op("sta", (N("b"),)),
            Op("jmp", (N("loop"),)),
            Label("a"),
            V(1),
            Label("b"),
            V(1),
        )
    )


def test_parse_unary_with_val() -> None:
    parser = Parser.from_str("lda 1")
    file = parser.parse_file()
    assert file == File((Op("lda", (V(1),)),))


def test_parse_nullary_or_val_invalid() -> None:
    parser = Parser.from_str("!!!")

    with pytest.raises(Stop) as excinfo:
        parser.parse_file()

    assert "is not a valid name or expression" in excinfo.value.msg


def test_parse_unary_invalid_mnemonic() -> None:
    parser = Parser.from_str("!!! blah")

    with pytest.raises(Stop) as excinfo:
        parser.parse_file()

    assert "is not a valid name or expression" in excinfo.value.msg


def test_parse_unary_invalid_op_arg() -> None:
    parser = Parser.from_str("blah !!!")

    with pytest.raises(Stop) as excinfo:
        parser.parse_file()

    assert "expected expression after mnemonic 'blah'" in excinfo.value.msg


def test_parse_binary_expected_comma() -> None:
    parser = Parser.from_str("foo bar baz")

    with pytest.raises(Stop) as excinfo:
        parser.parse_file()

    assert "expected ','" in excinfo.value.msg


def test_parse_binary_expected_text() -> None:
    parser = Parser.from_str("foo bar,")

    with pytest.raises(Stop) as excinfo:
        parser.parse_file()

    assert "expected expression after ','" in excinfo.value.msg


def test_parse_binary_expected_newline() -> None:
    parser = Parser.from_str("foo bar, baz bing")

    with pytest.raises(Stop) as excinfo:
        parser.parse_file()

    assert "expected end of line" in excinfo.value.msg


def test_parse_binary_expected_mnemonic() -> None:
    parser = Parser.from_str("!!! bar, baz")

    with pytest.raises(Stop) as excinfo:
        parser.parse_file()

    assert "is not a valid name or expression" in excinfo.value.msg


def test_parse_binary() -> None:
    parser = Parser.from_str("foo bar, 42")
    file = parser.parse_file()
    assert file == File((Op("foo", (N("bar"), V(42))),))


def test_parser_from_buf() -> None:
    buf = StringIO("foo")
    parser = Parser.from_buf(buf)

    assert parser.parse_file() == File((N("foo"),))


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


def test_parse_const() -> None:
    parser = Parser.from_str("foo = 42")
    file = parser.parse_file()
    assert file == File((Const("foo", V(42)),))


def test_invalid_const_name() -> None:
    parser = Parser.from_str("foo!#@$ = 0")

    with pytest.raises(Stop) as excinfo:
        parser.parse_const()

    assert "is not a valid name" in excinfo.value.msg


def test_invalid_const_expression() -> None:
    parser = Parser.from_str("foo =")

    with pytest.raises(Stop) as excinfo:
        parser.parse_const()

    assert "expected expression after '='" in excinfo.value.msg


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
+2:
  foo
-1:
  bar
"""
    )
    file = parser.parse_file()
    assert file == File(
        (
            Offset(0x8000, None),
            Label("start"),
            Op("lda", (V(42),)),
            N("hlt"),
            Offset(0xFFFC, None),
            Op("word", (N("start"),)),
            Offset(0xFFFE, None),
            Op("word", (V(0),)),
            Offset(2, "+"),
            N("foo"),
            Offset(1, "-"),
            N("bar"),
        )
    )


def test_invalid_label_name() -> None:
    parser = Parser.from_str("foo!#@$: 0")

    with pytest.raises(Stop) as excinfo:
        parser.parse_label()

    assert "is not a valid name or offset" in excinfo.value.msg


def test_invalid_forward_offset_val() -> None:
    parser = Parser.from_str("+foo: 0")

    with pytest.raises(Stop) as excinfo:
        parser.parse_offset()

    assert "is not a valid offset" in excinfo.value.msg


def test_invalid_backward_offset_val() -> None:
    parser = Parser.from_str("-foo: 0")

    with pytest.raises(Stop) as excinfo:
        parser.parse_offset()

    assert "is not a valid offset" in excinfo.value.msg


@pytest.mark.parametrize(
    "method_name,file_txt,expected",
    (
        # ========= parse_atom =========
        ("parse_atom", "0", V(0)),
        ("parse_atom", "foo", N("foo")),
        ("parse_atom", "(foo)", N("foo")),
        ("parse_atom", "[foo]", N("foo")),
        ("parse_atom", "!!!", None),
        # hard failures
        ("parse_atom", "(!!!)", Eq("expected expression after '('")),
        ("parse_atom", "[!!!]", Eq("expected expression after '['")),
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
    "file_txt,scope,expected",
    (
        ("42", {}, 42),
        ("foo", {"foo": 42}, 42),
        ("-1", {}, -1),
        ("~0", {}, -1),
        ("5 | 4", {}, 5),
        ("5 ^ 6", {}, 3),
        ("5 & 6", {}, 4),
        ("5 >> 1", {}, 2),
        ("5 << 1", {}, 10),
        ("2 + 3", {}, 5),
        ("2 - 3", {}, -1),
        ("2 * 3", {}, 6),
        ("5 / 3", {}, 1),
        ("5 % 3", {}, 2),
        ("2 ** 4", {}, 16),
        ("x - y", {"x": 2, "y": 3}, -1),
        ("-(2 ** 8)", {}, -256),
        ("2 + 3 * 4", {}, 14),
        ("2 * 3 + 4", {}, 10),
        ("foo", {}, In("name 'foo' is not bound")),
    ),
)
def test_expr_eval(file_txt: str, scope: Dict[str, int], expected: Any) -> None:
    parser = Parser.from_str(file_txt)
    file = parser.parse_file()
    expr = cast(Expr, file.stmts[0])

    if isinstance(expected, int):
        actual = expr.eval(scope)

        assert actual == expected
    elif isinstance(expected, Predicate):
        with pytest.raises(Message) as excinfo:
            expr.eval(scope)

        assert expected(excinfo.value.msg)


def test_expr_is_deref() -> None:
    parser = Parser.from_str("foo")
    file = parser.parse_file()
    expr = cast(Expr, file.stmts[0])

    assert not expr.is_deref

    parser = Parser.from_str("foo [bar]")
    file = parser.parse_file()
    op = cast(Op, file.stmts[0])
    expr = op.args[0]

    assert expr.is_deref


def test_parse_deref_error() -> None:
    parser = Parser.from_str("foo [!!!]")
    with pytest.raises(Stop) as excinfo:
        parser.parse_file()

    assert "expected expression after '['" in excinfo.value.msg
