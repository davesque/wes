from typing import Callable, List, Union

import pytest

from wes.compiler import Compiler
from wes.compilers.sap import CompileSap
from wes.exceptions import Message
from wes.instruction import Word

from .utils import Eq, In, Predicate


@pytest.mark.parametrize(
    "file_txt,expected",
    (
        ("word 0", [0, 0]),
        ("word foo\nfoo: 1", [2, 0, 1]),
        ("256", Eq("evaluated result '256' is too large")),
        ("hlt 42", Eq("'hlt' instruction takes no argument")),
        ("lda", Eq("'lda' instruction takes one argument")),
        ("hlt", [0xF0]),
    ),
)
def test_instructions(file_txt: str, expected: Union[List[int], Predicate]) -> None:
    compiler = CompileSap.from_str(file_txt)

    if isinstance(expected, Predicate):
        with pytest.raises(Message) as excinfo:
            list(compiler)

        assert expected(excinfo.value.msg)
    else:
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
