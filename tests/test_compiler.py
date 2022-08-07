from io import StringIO
from typing import Callable, cast

import pytest

from wes.compilers.sap import Lda, SapCompiler
from wes.exceptions import Message
from wes.instruction import Value
from wes.parser import Op, Val

from .utils import Eq, In, Re


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
foo 42 ; invalid instruction
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

    def test_scan(self) -> None:
        compiler = SapCompiler.from_str(
            """
x = 5
y = 6
z = x + y
zero: 0x42
word 0xffff
0
w = x + y + z
-1:
fifteen: 0x44
    """
        )
        compiler.scan()

        assert len(compiler.labels) == 2
        assert len(compiler.consts) == 4
        assert len(compiler.scope) == 6

        assert compiler.labels["zero"] == 0
        assert compiler.labels["fifteen"] == 15

        assert compiler.consts["x"] == 5
        assert compiler.consts["y"] == 6
        assert compiler.consts["z"] == 11
        assert compiler.consts["w"] == 22

    @pytest.mark.parametrize(
        "file_txt,check_msg",
        (
            ("0\n0xf: 0\n0", In("makes program too large")),
            ("lda: 0", Eq("label 'lda' uses reserved name")),
            ("foo: 0\nfoo: 0", Eq("redefinition of label 'foo'")),
            ("-1: 0", In("offset must follow")),
            ("word 0\n-1: 0", In("size of padding instruction 'word'")),
            ("lda = 42", Eq("constant 'lda' uses reserved name")),
            ("foo = 42\nfoo = 0", Eq("redefinition of constant 'foo'")),
            ("foo: 0\nfoo = 0", Eq("label name 'foo' collides with constant name")),
        ),
    )
    def test_scan_errors(self, file_txt: str, check_msg: Callable[[str], bool]) -> None:
        compiler = SapCompiler.from_str(file_txt)

        with pytest.raises(Message) as excinfo:
            compiler.scan()

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
        compiler.scan()

        assert compiler.labels["label1"] == 3
        assert compiler.labels["label2"] == 10
        assert compiler.labels["label3"] == 15

    @pytest.mark.parametrize(
        "file_txt,check_msg",
        (
            ("0x10: 0", Eq("offset resolves to oversized location '16'")),
            ("0\n0\n0: 0", Re(r"^offset .* location '0' before current position$")),
        ),
    )
    def test_resolve_offsets_errors(
        self, file_txt: str, check_msg: Callable[[str], bool]
    ) -> None:
        compiler = SapCompiler.from_str(file_txt)

        with pytest.raises(Message) as excinfo:
            compiler.scan()

        assert check_msg(excinfo.value.msg)

    def test_resolve_label(self) -> None:
        compiler = SapCompiler.from_str(
            """
lda meaning_of_life
forty_two: 0x42
    """
        )
        compiler.scan()

        bad_label_tok = compiler.file.stmts[0].toks[1]
        with pytest.raises(Message) as excinfo:
            compiler.resolve_label("meaning_of_life", bad_label_tok)
        assert excinfo.value.msg == "unrecognized label 'meaning_of_life'"
        assert excinfo.value.toks == (bad_label_tok,)

        good_label_tok = compiler.file.stmts[1].toks[1]
        assert compiler.resolve_label("forty_two", good_label_tok) == 1

    def test_compile_basic(self) -> None:
        # fmt: off
        expected_output = (
            [0b00010100, 0b11100000, 0b00100101, 0b01100001, 0b00101010, 0b00000001]
        )
        # fmt: on

        compiler = SapCompiler.from_str(
            """
lda init

loop:
  out
  add incr
  jmp loop

init: 42
incr: 1
    """
        )
        assert list(compiler) == expected_output

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

    def test_compile_constants(self) -> None:
        # fmt: off
        expected_output = (
            [0b00010100, 0b11100000, 0b00100101, 0b01100001, 0b00101010, 0b00000001]
        )
        # fmt: on

        compiler = SapCompiler.from_str(
            """
init_val = 42
incr_val = 1

lda init

loop:
  out
  add incr
  jmp loop

init: init_val
incr: incr_val
    """
        )
        assert list(compiler) == expected_output
