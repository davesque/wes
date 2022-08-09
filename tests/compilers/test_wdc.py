from typing import List, Union

import pytest

from wes.compilers.wdc import Compile6502
from wes.exceptions import Message

from ..utils import Predicate, Re


@pytest.mark.parametrize(
    "file_txt,expected",
    (
        ("lda 0x10", [0xA9, 0x10]),
        (
            "lda 0x100",
            Re(r"^instruction 'lda' .* addressing mode 'IMM' .* operand '256'$"),
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
