from typing import List, Tuple, Union

import pytest

from wes.compilers.wdc import Compile6502, Format
from wes.exceptions import Message
from wes.parser import BinExpr, Expr, Name, Parser, Val

from ..utils import Eq, Predicate


@pytest.mark.parametrize(
    "expr_str,expected",
    (
        ("[[(a + b) + x]]", (Format.IDX_IND, BinExpr(Name("a"), "+", Name("b")))),
        ("[[foo]]", (Format.IND, Name("foo"))),
        ("[[_] + y]", (Format.IND_Y, Name("_"))),
        ("[42 + x]", (Format.IDX_X, Val(42))),
        ("[42 + y]", (Format.IDX_Y, Val(42))),
        ("[42]", (Format.DIR, Val(42))),
        ("42", (Format.IMM, Val(42))),
        ("(a ** b)", (Format.IMM, BinExpr(Name("a"), "**", Name("b")))),
    ),
)
def test_format_match(expr_str: str, expected: Tuple[Format, Expr]) -> None:
    parser = Parser.from_str(expr_str)

    expr = parser.parse_expr()
    assert expr is not None

    fmt, arg = Format.match(expr)
    assert (fmt, arg) == expected


@pytest.mark.parametrize(
    "file_txt,expected",
    (
        ("nop", [0xEA]),
        # WdcUnary errors
        (
            "lda 0x10000",
            Eq("evaluated result '65536' does not fit in two bytes"),
        ),
        (
            "lda 0x100",
            Eq(
                "instruction 'lda' "
                + "does not support addressing mode 'immediate' "
                + "for 2 byte operands"
            ),
        ),
        # LDA
        ("lda [0x100]", [0xAD, 0x00, 0x01]),
        ("lda [0x100 + x]", [0xBD, 0x00, 0x01]),
        ("lda [0x100 + y]", [0xB9, 0x00, 0x01]),
        ("lda 0xff", [0xA9, 0xFF]),
        ("lda [0xff]", [0xA5, 0xFF]),
        ("lda [[0xff + x]]", [0xA1, 0xFF]),
        ("lda [0xff + x]", [0xB5, 0xFF]),
        ("lda [[0xff]]", [0xB2, 0xFF]),
        ("lda [[0xff] + y]", [0xB1, 0xFF]),
        # LDX
        ("ldx [0x100]", [0xAE, 0x00, 0x01]),
        ("ldx [0x100 + y]", [0xBE, 0x00, 0x01]),
        ("ldx 0xff", [0xA2, 0xFF]),
        ("ldx [0xff]", [0xA6, 0xFF]),
        ("ldx [0xff + y]", [0xB6, 0xFF]),
    ),
)
def test_wdc_instructions(file_txt: str, expected: Union[List[int], Predicate]) -> None:
    compiler = Compile6502.from_str(file_txt)

    if isinstance(expected, Predicate):
        with pytest.raises(Message) as excinfo:
            list(compiler)

        assert expected(excinfo.value.msg)
    else:
        assert list(compiler) == expected
