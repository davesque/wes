from typing import List, Union, Tuple

import pytest

from wes.compilers.wdc import Compile6502, Format
from wes.parser import Expr, Val, Parser, BinExpr, Name
from wes.exceptions import Message

from ..utils import Predicate, Re


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
        ("lda 0x10", [0xA9, 0x10]),
        (
            "lda 0x100",
            Re(r"^instruction 'lda' .* addressing mode 'immediate' .* operand '256'$"),
        ),
    ),
)
def test_sap_instructions(file_txt: str, expected: Union[List[int], Predicate]) -> None:
    compiler = Compile6502.from_str(file_txt)

    if isinstance(expected, Predicate):
        with pytest.raises(Message) as excinfo:
            list(compiler)

        assert expected(excinfo.value.msg)
    else:
        assert list(compiler) == expected
