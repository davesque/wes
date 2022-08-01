from typing import Callable, List

import pytest

from wes.compiler import Compiler
from wes.compilers.sap import SapCompiler
from wes.exceptions import Message
from wes.instruction import Word

from .utils import In


@pytest.mark.parametrize(
    "file_txt,expected",
    (
        ("word 0", [0, 0]),
        ("word foo\nfoo: 1", [2, 0, 1]),
    ),
)
def test_word(file_txt: str, expected: List[int]) -> None:
    compiler = SapCompiler.from_str(file_txt)

    assert list(compiler) == expected


class WordErrorCompiler(Compiler):
    max_addr = 2**24 - 1

    instructions = {
        Word.mnemonic: Word,
    }


@pytest.mark.parametrize(
    "file_txt,check_msg",
    (
        ("word 0x10000", In("evaluated result '65536' does not fit")),
        (
            "0\nword end\n-1: end: 0",
            In("evaluated result '16777215' does not fit"),
        ),
    ),
)
def test_word_error(file_txt: str, check_msg: Callable[[str], bool]) -> None:
    compiler = WordErrorCompiler.from_str(file_txt)

    with pytest.raises(Message) as excinfo:
        list(compiler)

    assert check_msg(excinfo.value.msg)
