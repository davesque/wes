import re
from io import StringIO
from typing import Callable, cast

import pytest

from das.compilers.sap import Lda, SapCompiler
from das.exceptions import Message
from das.instruction import Value
from das.parser import Op, Val


def eq_(x: str) -> Callable[[str], bool]:
    def f(y: str) -> bool:
        return x == y

    return f


def re_(pat: str) -> Callable[[str], bool]:
    pat_re = re.compile(pat)

    def f(s: str) -> bool:
        return bool(pat_re.match(s))

    return f


def in_(x: str) -> Callable[[str], bool]:
    def f(y: str) -> bool:
        return x in y

    return f


class TestCompiler:
    def test_from_str(self) -> None:
        assert list(SapCompiler.from_str("255")) == [255]

    def test_from_buf(self) -> None:
        assert list(SapCompiler.from_buf(StringIO("255"))) == [255]

    def test_get_instruction(self) -> None:
        compiler = SapCompiler.from_str(
            """
lda 1  ; valid op
2      ; valid value
foo    ; invalid instruction
"""
        )
        file = compiler.file

        lda_stmt = file.stmts[0]
        val_stmt = file.stmts[1]
        foo_stmt = file.stmts[2]

        lda_inst = compiler.get_instruction(cast(Op, lda_stmt))
        assert isinstance(lda_inst, Lda)
        assert lda_inst.compiler is compiler
        assert lda_inst.op is lda_stmt

        val_inst = compiler.get_instruction(cast(Val, val_stmt))
        assert isinstance(val_inst, Value)
        assert val_inst.compiler is compiler
        assert val_inst.val is val_stmt

        with pytest.raises(Message) as excinfo:
            compiler.get_instruction(cast(Op, foo_stmt))

        assert excinfo.value.msg == "unrecognized instruction 'foo'"

    def test_find_labels(self) -> None:
        compiler = SapCompiler.from_str(
            """
zero: 0x42
word 0xffff
0
-1:
fifteen: 0x44
    """
        )
        compiler.find_labels()

        assert len(compiler.labels) == 2

        assert compiler.labels["zero"] == 0
        assert compiler.labels["fifteen"] == 15

    @pytest.mark.parametrize(
        "file_txt,check_msg",
        (
            ("0\n0xf: 0\n0", in_("makes program too large")),
            ("lda: 0", eq_("label 'lda' uses reserved name")),
            ("foo: 0\nfoo: 0", eq_("redefinition of label 'foo'")),
            ("-1: 0", in_("offset must follow")),
            ("word 0\n-1: 0", in_("size of padding instruction 'word'")),
        ),
    )
    def test_find_labels_errors(
        self, file_txt: str, check_msg: Callable[[str], bool]
    ) -> None:
        compiler = SapCompiler.from_str(file_txt)

        with pytest.raises(Message) as excinfo:
            compiler.find_labels()

        assert check_msg(excinfo.value.msg)

    def test_resolve_offsets(self) -> None:
        compiler = SapCompiler.from_str(
            """
0
+2:
label1: 0
0xa:
label2: 0
-1:
label3: 0
    """
        )
        compiler.find_labels()

        assert compiler.labels["label1"] == 3
        assert compiler.labels["label2"] == 10
        assert compiler.labels["label3"] == 15

    @pytest.mark.parametrize(
        "file_txt,check_msg",
        (
            ("0x10: 0", re_(r"^offset '0x10' resolves .* address '16'$")),
            ("0\n0\n0: 0", re_(r"^offset '0' is before.*$")),
        ),
    )
    def test_resolve_offsets_errors(
        self, file_txt: str, check_msg: Callable[[str], bool]
    ) -> None:
        compiler = SapCompiler.from_str(file_txt)

        with pytest.raises(Message) as excinfo:
            compiler.find_labels()

        assert check_msg(excinfo.value.msg)

    def test_resolve_label(self) -> None:
        compiler = SapCompiler.from_str(
            """
    lda meaning_of_life
    forty_two: 0x42
    """
        )
        compiler.find_labels()

        bad_label_tok = compiler.file.stmts[0].toks[1]
        with pytest.raises(Message) as excinfo:
            compiler.resolve_label("meaning_of_life", bad_label_tok)
        assert excinfo.value.msg == "unrecognized label 'meaning_of_life'"
        assert excinfo.value.toks == (bad_label_tok,)

        good_label_tok = compiler.file.stmts[1].toks[1]
        assert compiler.resolve_label("forty_two", good_label_tok) == 1

    def test_compile_offsets(self) -> None:
        # fmt: off
        expected_output = (
            [0b00011110, 0b11100000, 0b00101111, 0b01100001] +
            [0] * 10 +
            [0b00101010, 0b00000001]
        )
        # fmt: on

        compiler = SapCompiler.from_str(
            """
    lda init

    loop:
      out
      add incr
      jmp loop

    nop  ; ...
    -2:

    init: 42
    incr: 1
    """
        )
        assert list(compiler) == expected_output

        compiler = SapCompiler.from_str(
            """
    lda init

    loop:
      out
      add incr
      jmp loop

    nop  ; ...
    0xe:

    init: 42
    incr: 1
    """
        )
        assert list(compiler) == expected_output

        compiler = SapCompiler.from_str(
            """
    lda init

    loop:
      out
      add incr
      jmp loop

    nop  ; ...
    +9:

    init: 42
    incr: 1
    """
        )
        assert list(compiler) == expected_output
