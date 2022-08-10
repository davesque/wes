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
            "lda",
            Eq("instruction 'lda' expects an argument"),
        ),
        (
            "lda foo, bar",
            Eq("instruction 'lda' expects one argument"),
        ),
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
        # RelativeUnary errors
        ("bbr0", Eq("instruction 'bbr0' expects an argument")),
        ("bbr0 foo, bar", Eq("instruction 'bbr0' expects one argument")),
        ("bbr0 256", Eq("evaluated result '256' does not fit in one byte")),
        # ADC
        ("adc [0x100]", [0x6D, 0x00, 0x01]),
        ("adc [0x100 + x]", [0x7D, 0x00, 0x01]),
        ("adc [0x100 + y]", [0x79, 0x00, 0x01]),
        ("adc 0xff", [0x69, 0xFF]),
        ("adc [0xff]", [0x65, 0xFF]),
        ("adc [[0xff + x]]", [0x61, 0xFF]),
        ("adc [0xff + x]", [0x75, 0xFF]),
        ("adc [[0xff]]", [0x72, 0xFF]),
        ("adc [[0xff] + y]", [0x71, 0xFF]),
        # AND
        ("and [0x100]", [0x2D, 0x00, 0x01]),
        ("and [0x100 + x]", [0x3D, 0x00, 0x01]),
        ("and [0x100 + y]", [0x39, 0x00, 0x01]),
        ("and 0xff", [0x29, 0xFF]),
        ("and [0xff]", [0x25, 0xFF]),
        ("and [[0xff + x]]", [0x21, 0xFF]),
        ("and [0xff + x]", [0x35, 0xFF]),
        ("and [[0xff]]", [0x32, 0xFF]),
        ("and [[0xff] + y]", [0x31, 0xFF]),
        # ASL
        ("asl [0x100]", [0x0E, 0x00, 0x01]),
        ("asl [0x100 + x]", [0x1E, 0x00, 0x01]),
        ("asl", [0x0A]),
        ("asl [0xff]", [0x06, 0xFF]),
        ("asl [0xff + x]", [0x16, 0xFF]),
        # BBRX
        ("bbr0 0xff", [0x0F, 0xFF]),
        ("bbr1 0xff", [0x1F, 0xFF]),
        ("bbr2 0xff", [0x2F, 0xFF]),
        ("bbr3 0xff", [0x3F, 0xFF]),
        ("bbr4 0xff", [0x4F, 0xFF]),
        ("bbr5 0xff", [0x5F, 0xFF]),
        ("bbr6 0xff", [0x6F, 0xFF]),
        ("bbr7 0xff", [0x7F, 0xFF]),
        # BBSX
        ("bbs0 0xff", [0x8F, 0xFF]),
        ("bbs1 0xff", [0x9F, 0xFF]),
        ("bbs2 0xff", [0xAF, 0xFF]),
        ("bbs3 0xff", [0xBF, 0xFF]),
        ("bbs4 0xff", [0xCF, 0xFF]),
        ("bbs5 0xff", [0xDF, 0xFF]),
        ("bbs6 0xff", [0xEF, 0xFF]),
        ("bbs7 0xff", [0xFF, 0xFF]),
        # Other branch
        ("bcc 0xff", [0x90, 0xFF]),
        ("bcs 0xff", [0xB0, 0xFF]),
        ("beq 0xff", [0xF0, 0xFF]),
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
